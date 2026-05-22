from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"
DEFAULT_STARS_MIN = 100
MAX_SEARCH_PAGES = 5


class GitHubAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class Issue:
    repo: str
    title: str
    url: str
    language: str
    stars: int
    labels: tuple[str, ...]
    updated_days: int
    repo_last_issue_updated_days: int
    repo_beginner_issue_count: int
    comments: int
    has_open_pr: bool


def search_issues(
    *,
    language: str | None = None,
    stars_min: int | None = None,
    label: str | None = None,
    updated_days: int | None = None,
    repo_updated_days: int | None = None,
    limit: int = 10,
) -> list[Issue]:
    effective_stars_min = max(stars_min or DEFAULT_STARS_MIN, DEFAULT_STARS_MIN)

    query = _build_issue_query(
        language=language,
        stars_min=effective_stars_min,
        label=label,
        updated_days=updated_days,
    )
    repo_cache: dict[str, dict[str, Any]] = {}
    repo_activity_cache: dict[str, int] = {}
    repo_beginner_issue_count_cache: dict[str, int] = {}
    issues: list[Issue] = []
    # Search candidates match the GitHub query first, then local filters below
    # enforce repo metadata and repo activity rules.
    per_page = min(max(limit * 10, 30), 100)

    for page in range(1, MAX_SEARCH_PAGES + 1):
        data = _request_json(
            "/search/issues",
            {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": str(per_page),
                "page": str(page),
            },
        )
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            if "pull_request" in item:
                continue

            repo = _repo_full_name(item)
            if repo is None:
                continue

            if repo not in repo_cache:
                repo_cache[repo] = _repo_info_from_search_result(item) or _get_repo(repo)
            repo_info = repo_cache[repo]
            stars = int(repo_info.get("stargazers_count") or 0)
            if stars < effective_stars_min:
                continue

            repo_language = str(repo_info.get("language") or "")
            if language and repo_language.casefold() != language.casefold():
                continue

            if repo not in repo_activity_cache:
                repo_activity_cache[repo] = _get_repo_last_issue_updated_days(repo)
            if repo not in repo_beginner_issue_count_cache:
                repo_beginner_issue_count_cache[repo] = _get_repo_beginner_issue_count(repo)
            if (
                repo_updated_days is not None
                and repo_activity_cache[repo] > repo_updated_days
            ):
                continue

            issue = Issue(
                repo=repo,
                title=str(item.get("title") or ""),
                url=str(item.get("html_url") or ""),
                language=repo_language,
                stars=stars,
                labels=_labels(item),
                updated_days=_days_since(str(item.get("updated_at") or "")),
                repo_last_issue_updated_days=repo_activity_cache[repo],
                repo_beginner_issue_count=repo_beginner_issue_count_cache[repo],
                comments=int(item.get("comments") or 0),
                has_open_pr=False,
            )
            issues.append(issue)
            if len(issues) >= limit:
                break

        if len(issues) >= limit or len(items) < per_page:
            break

    return issues


def _build_issue_query(
    *,
    language: str | None,
    stars_min: int | None,
    label: str | None,
    updated_days: int | None,
) -> str:
    parts = ["is:issue", "is:open", "archived:false", "-linked:pr", "no:assignee"]
    if language:
        parts.append(f"language:{_quote_query_value(language)}")
    if label:
        parts.append(f"label:{_quote_query_value(label)}")
    if updated_days is not None:
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=updated_days)
        parts.append(f"updated:>={cutoff.isoformat()}")
    return " ".join(parts)


def _request_json(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    url = f"{GITHUB_API_BASE}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "oss-issue-scout",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        if error.code == 403 and "rate limit" in message.casefold():
            raise GitHubAPIError(
                "GitHub API rate limit exceeded. Set a GITHUB_TOKEN environment "
                "variable to get a higher rate limit, then try again."
            ) from error
        raise GitHubAPIError(f"GitHub API request failed: HTTP {error.code} {message}") from error
    except URLError as error:
        raise GitHubAPIError(f"GitHub API request failed: {error.reason}") from error


def _get_repo(repo: str) -> dict[str, Any]:
    owner, name = repo.split("/", 1)
    return _request_json(f"/repos/{quote(owner)}/{quote(name)}")


def _get_repo_last_issue_updated_days(repo: str) -> int:
    data = _request_json(
        "/search/issues",
        {
            "q": f"repo:{repo} is:issue",
            "sort": "updated",
            "order": "desc",
            "per_page": "1",
        },
    )
    items = data.get("items", [])
    if not items:
        return 9999
    return _days_since(str(items[0].get("updated_at") or ""))


def _get_repo_beginner_issue_count(repo: str) -> int:
    data = _request_json(
        "/search/issues",
        {
            "q": f'repo:{repo} is:issue is:open label:"good first issue","help wanted"',
            "per_page": "1",
        },
    )
    return int(data.get("total_count") or 0)


def _repo_full_name(item: dict[str, Any]) -> str | None:
    repository_url = str(item.get("repository_url") or "")
    marker = f"{GITHUB_API_BASE}/repos/"
    if repository_url.startswith(marker):
        return repository_url.removeprefix(marker)
    repository = item.get("repository")
    if isinstance(repository, dict):
        full_name = repository.get("full_name")
        if isinstance(full_name, str):
            return full_name
    return None


def _repo_info_from_search_result(item: dict[str, Any]) -> dict[str, Any] | None:
    repository = item.get("repository")
    if not isinstance(repository, dict):
        return None
    if "stargazers_count" not in repository or "language" not in repository:
        return None
    return repository


def _labels(item: dict[str, Any]) -> tuple[str, ...]:
    labels = item.get("labels") or []
    names: list[str] = []
    for label in labels:
        if isinstance(label, dict) and isinstance(label.get("name"), str):
            names.append(label["name"])
    return tuple(names)


def _days_since(value: str) -> int:
    if not value:
        return 9999
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - timestamp
    return max(delta.days, 0)


def _quote_query_value(value: str) -> str:
    if " " in value:
        return f'"{value}"'
    return value

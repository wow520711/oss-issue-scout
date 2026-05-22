import unittest
from unittest.mock import patch

from oss_issue_scout.github_api import _build_issue_query, search_issues


class SearchIssuesTests(unittest.TestCase):
    def test_query_requires_unassigned_issues(self) -> None:
        query = _build_issue_query(
            language=None,
            stars_min=None,
            label=None,
            updated_days=None,
        )

        self.assertIn("no:assignee", query)

    def test_searches_github_and_maps_results(self) -> None:
        with patch("oss_issue_scout.github_api._request_json", side_effect=_fake_request_json):
            issues = search_issues(language="python", label="good first issue", updated_days=10, limit=5)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].repo, "example/project")
        self.assertEqual(issues[0].stars, 12_000)
        self.assertEqual(issues[0].labels, ("good first issue",))
        self.assertEqual(issues[0].repo_beginner_issue_count, 3)
        self.assertFalse(issues[0].has_open_pr)

    def test_filters_by_min_stars_after_repo_lookup(self) -> None:
        with patch("oss_issue_scout.github_api._request_json", side_effect=_fake_request_json):
            issues = search_issues(stars_min=50_000, limit=5)

        self.assertEqual(issues, [])

    def test_skips_repos_with_fewer_than_default_min_stars(self) -> None:
        with patch("oss_issue_scout.github_api._request_json", side_effect=_fake_low_star_repo):
            issues = search_issues(limit=5)

        self.assertEqual(issues, [])

    def test_filters_by_repo_issue_activity_after_lookup(self) -> None:
        with patch("oss_issue_scout.github_api._request_json", side_effect=_fake_stale_repo_activity):
            issues = search_issues(repo_updated_days=7, limit=5)

        self.assertEqual(issues, [])

    def test_fetches_more_pages_when_candidates_are_filtered(self) -> None:
        with patch("oss_issue_scout.github_api._request_json", side_effect=_fake_paginated_request_json):
            issues = search_issues(language="python", limit=2)

        self.assertEqual([issue.repo for issue in issues], ["example/one", "example/two"])


def _fake_request_json(path: str, params: dict[str, str] | None = None) -> dict:
    if (
        path == "/search/issues"
        and params
        and params.get("per_page") == "1"
        and "label:" in params.get("q", "")
    ):
        return {"total_count": 3, "items": []}

    if path == "/search/issues" and params and params.get("per_page") == "1":
        return {
            "items": [
                {
                    "updated_at": "2026-05-20T00:00:00Z",
                }
            ]
        }

    if path == "/search/issues":
        return {
            "items": [
                {
                    "title": "Improve docs",
                    "html_url": "https://github.com/example/project/issues/1",
                    "repository_url": "https://api.github.com/repos/example/project",
                    "repository": {
                        "full_name": "example/project",
                        "language": "Python",
                        "stargazers_count": 12_000,
                    },
                    "labels": [{"name": "good first issue"}],
                    "updated_at": "2026-05-19T00:00:00Z",
                    "comments": 1,
                },
                {
                    "title": "Open pull request",
                    "html_url": "https://github.com/example/project/pull/2",
                    "repository_url": "https://api.github.com/repos/example/project",
                    "repository": {
                        "full_name": "example/project",
                        "language": "Python",
                        "stargazers_count": 12_000,
                    },
                    "labels": [],
                    "updated_at": "2026-05-19T00:00:00Z",
                    "comments": 0,
                    "pull_request": {},
                },
            ]
        }

    if path == "/repos/example/project":
        return {
            "full_name": "example/project",
            "language": "Python",
            "stargazers_count": 12_000,
        }

    raise AssertionError(f"Unexpected API request: {path} {params}")


def _fake_stale_repo_activity(path: str, params: dict[str, str] | None = None) -> dict:
    if path == "/search/issues" and params and params.get("per_page") == "1":
        return {
            "items": [
                {
                    "updated_at": "2026-04-01T00:00:00Z",
                }
            ]
        }
    return _fake_request_json(path, params)


def _fake_low_star_repo(path: str, params: dict[str, str] | None = None) -> dict:
    if path == "/search/issues" and params and params.get("per_page") == "1":
        return _fake_request_json(path, params)
    if path == "/search/issues":
        data = _fake_request_json(path, params)
        data["items"][0]["repository"]["stargazers_count"] = 99
        return data
    return _fake_request_json(path, params)


def _fake_paginated_request_json(path: str, params: dict[str, str] | None = None) -> dict:
    if (
        path == "/search/issues"
        and params
        and params.get("per_page") == "1"
        and "label:" in params.get("q", "")
    ):
        return {"total_count": 3, "items": []}

    if path == "/search/issues" and params and params.get("per_page") == "1":
        return {"items": [{"updated_at": "2026-05-20T00:00:00Z"}]}

    if path == "/search/issues" and params and params.get("page") == "1":
        per_page = int(params["per_page"])
        return {
            "items": [
                _github_issue_item(
                    repo=f"example/filtered-{index}",
                    stars=99,
                    title=f"Filtered {index}",
                )
                for index in range(per_page)
            ]
        }

    if path == "/search/issues" and params and params.get("page") == "2":
        return {
            "items": [
                _github_issue_item(repo="example/one", stars=12_000, title="One"),
                _github_issue_item(repo="example/two", stars=12_000, title="Two"),
            ]
        }

    raise AssertionError(f"Unexpected API request: {path} {params}")


def _github_issue_item(*, repo: str, stars: int, title: str) -> dict:
    return {
        "title": title,
        "html_url": f"https://github.com/{repo}/issues/1",
        "repository_url": f"https://api.github.com/repos/{repo}",
        "repository": {
            "full_name": repo,
            "language": "Python",
            "stargazers_count": stars,
        },
        "labels": [{"name": "good first issue"}],
        "updated_at": "2026-05-19T00:00:00Z",
        "comments": 1,
    }


if __name__ == "__main__":
    unittest.main()

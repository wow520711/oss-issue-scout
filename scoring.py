from __future__ import annotations

from dataclasses import dataclass

from github_api import Issue


@dataclass(frozen=True)
class ScoredIssue:
    issue: Issue
    score: int
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


def score_issue(issue: Issue) -> ScoredIssue:

    score = 50
    reasons: list[str] = []
    warnings: list[str] = []

    if issue.stars >= 100_000:
        score -= 15
        warnings.append("very large repo may be competitive")
    elif issue.stars >= 50_000:
        score -= 10
        warnings.append("large repo may be competitive")
    elif issue.stars >= 10_000:
        score += 15
        reasons.append("active repo")
    elif issue.stars >= 5_000:
        score += 10
        reasons.append("moderately active repo")
    elif issue.stars >= 500:
        score += 5
        reasons.append("somewhat active repo")


    if issue.updated_days <= 1:
        score += 15
        reasons.append("issue updated today")
    elif issue.updated_days <= 3:
        score += 10
        reasons.append("issue updated in the last 3 days")
    elif issue.updated_days <= 14:
        score += 5
        reasons.append("issue updated in the last 2 weeks")
    elif issue.updated_days > 30:
        score -= 20
        warnings.append("issue looks stale")


    if issue.repo_last_issue_updated_days <= 3:
        score += 30
        reasons.append("repo issue activity in the last 3 days")
    elif issue.repo_last_issue_updated_days <= 7:
        score += 15
        reasons.append("repo issue activity this week")
    elif issue.repo_last_issue_updated_days <= 14:
        score -= 5
        warnings.append("repo issue activity is slowing")
    elif issue.repo_last_issue_updated_days <= 30:
        score -= 30
        warnings.append("repo issue activity looks stale")
    elif issue.repo_last_issue_updated_days > 30:
        score -= 40
        warnings.append("repo issue activity is stale")


    beginner_labels = {"good first issue", "help wanted"}
    if beginner_labels.intersection(issue.labels) and issue.repo_beginner_issue_count >= 3:
        score += 10
        reasons.append("welcoming label")

    if issue.comments <= 1:
        score += 15
        reasons.append("low discussion volume")
    elif issue.comments >= 5:
        score -= 15
        warnings.append("long discussion")

    return ScoredIssue(
        issue=issue,
        score=max(score, 0),
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def score_issues(issues: list[Issue]) -> list[ScoredIssue]:

    return sorted(
        (score_issue(issue) for issue in issues),
        key=lambda scored: scored.score,
        reverse=True,
    )

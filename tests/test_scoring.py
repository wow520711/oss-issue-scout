import unittest

from oss_issue_scout.github_api import Issue
from oss_issue_scout.scoring import score_issue, score_issues


class ScoringTests(unittest.TestCase):
    def test_score_contains_reasons(self) -> None:
        issue = Issue(
            repo="example/large",
            title="Improve docs",
            url="https://github.com/example/large/issues/1",
            language="python",
            stars=68_000,
            labels=("good first issue",),
            updated_days=2,
            repo_last_issue_updated_days=2,
            repo_beginner_issue_count=3,
            comments=1,
            has_open_pr=False,
        )

        scored = score_issue(issue)

        self.assertGreater(scored.score, 0)
        self.assertIn("large repo may be competitive", scored.warnings)
        self.assertIn("issue updated in the last 3 days", scored.reasons)
        self.assertIn("repo issue activity in the last 3 days", scored.reasons)

    def test_very_large_repos_are_penalized(self) -> None:
        issue = Issue(
            repo="example/huge",
            title="Small docs cleanup",
            url="https://github.com/example/huge/issues/1",
            language="python",
            stars=120_000,
            labels=("good first issue",),
            updated_days=2,
            repo_last_issue_updated_days=2,
            repo_beginner_issue_count=3,
            comments=1,
            has_open_pr=False,
        )

        scored = score_issue(issue)

        self.assertIn("very large repo may be competitive", scored.warnings)
        self.assertNotIn("active repo", scored.reasons)

    def test_score_issues_sorts_highest_first(self) -> None:
        issues = [
            Issue(
                repo="example/high",
                title="Small docs cleanup",
                url="https://github.com/example/high/issues/1",
                language="python",
                stars=12_000,
                labels=("good first issue",),
                updated_days=1,
                repo_last_issue_updated_days=1,
                repo_beginner_issue_count=3,
                comments=1,
                has_open_pr=False,
            ),
            Issue(
                repo="example/low",
                title="Long stale bug",
                url="https://github.com/example/low/issues/2",
                language="python",
                stars=80_000,
                labels=("bug",),
                updated_days=80,
                repo_last_issue_updated_days=80,
                repo_beginner_issue_count=0,
                comments=20,
                has_open_pr=False,
            ),
        ]
        scored = score_issues(issues)

        self.assertEqual(
            [result.score for result in scored],
            sorted((result.score for result in scored), reverse=True),
        )

    def test_beginner_label_bonus_requires_repo_depth(self) -> None:
        issue = Issue(
            repo="example/thin",
            title="Small docs cleanup",
            url="https://github.com/example/thin/issues/1",
            language="python",
            stars=12_000,
            labels=("good first issue",),
            updated_days=1,
            repo_last_issue_updated_days=1,
            repo_beginner_issue_count=2,
            comments=1,
            has_open_pr=False,
        )

        scored = score_issue(issue)

        self.assertNotIn("welcoming label", scored.reasons)


if __name__ == "__main__":
    unittest.main()

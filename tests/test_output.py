import json
import unittest

from github_api import Issue
from output import render_json, render_markdown, render_table
from scoring import score_issues


class OutputTests(unittest.TestCase):
    def setUp(self) -> None:
        issue = Issue(
            repo="example/project",
            title="Improve docs",
            url="https://github.com/example/project/issues/1",
            language="python",
            stars=12_000,
            labels=("good first issue",),
            updated_days=1,
            repo_last_issue_updated_days=1,
            repo_beginner_issue_count=3,
            comments=1,
            has_open_pr=False,
        )
        self.results = score_issues([issue])

    def test_renders_json(self) -> None:
        payload = json.loads(render_json(self.results))

        self.assertEqual(payload[0]["repo"], "example/project")
        self.assertIn("reasons", payload[0])

    def test_renders_markdown(self) -> None:
        rendered = render_markdown(self.results)

        self.assertIn("| Score | Repo | Issue | URL | Reasons | Warnings |", rendered)
        self.assertIn("example/project", rendered)

    def test_renders_table(self) -> None:
        rendered = render_table(self.results)

        self.assertIn("score", rendered)
        self.assertIn("example/project", rendered)


if __name__ == "__main__":
    unittest.main()

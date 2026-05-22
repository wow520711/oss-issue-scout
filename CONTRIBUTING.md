# Contributing

Thanks for your interest in oss-issue-scout.

This project is still an early MVP, so small, focused changes are preferred.

## Setup

No third-party dependencies are required for the current version.

To avoid GitHub API rate limits during manual testing, set a token:

```powershell
$env:GITHUB_TOKEN="your_token_here"
```

## Run

```powershell
python cli.py search --language python --label "good first issue" --limit 5
```

## Test

```powershell
python -m unittest discover
```

Unit tests use mocked GitHub responses and do not call the real GitHub API.

For a real API smoke test, run:

```powershell
python cli.py search --language python --label "good first issue" --limit 3
```

## Guidelines

- Keep changes small and easy to review.
- Do not add new dependencies unless they are clearly needed.
- Keep CLI behavior simple and documented.
- Prefer tests for scoring, filtering, output, and error handling changes.

## Pull Requests

Before opening a PR, please run:

```powershell
python -m unittest discover
```

In the PR description, briefly mention:

- What changed
- How you tested it
- Any GitHub API or rate-limit considerations

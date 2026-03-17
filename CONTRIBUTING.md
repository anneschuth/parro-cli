# Contributing to parro

Thanks for your interest in contributing!

## Development setup

```bash
git clone https://github.com/anneschuth/parro-cli.git
cd parro-cli
uv sync --extra dev
uv run pre-commit install
uv run pytest
```

## Pre-commit hooks

This project uses [pre-commit](https://pre-commit.com/) with [ruff](https://docs.astral.sh/ruff/) for linting and formatting. Hooks run automatically on `git commit`.

To run manually on all files:

```bash
uv run pre-commit run --all-files
```

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `style:` | Formatting, no logic change |
| `refactor:` | Code restructure, no behavior change |
| `test:` | Adding or updating tests |
| `chore:` | Maintenance (deps, CI, config) |
| `ci:` | CI/CD changes |
| `perf:` | Performance improvement |

These messages are used by [python-semantic-release](https://python-semantic-release.readthedocs.io/) to automatically determine version bumps and generate changelogs.

## Pull requests

1. Fork the repo and create a feature branch
2. Make your changes with appropriate tests
3. Ensure `uv run pytest` and `uv run pre-commit run --all-files` pass
4. Open a PR against `main`

## Language conventions

- **CLI output** is in Dutch (the target audience is Dutch parents)
- **Code, docstrings, and comments** are in English
- **Commit messages** are in English

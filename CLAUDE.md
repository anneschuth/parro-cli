# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Parro CLI — a Python command-line client for the Parro school communication platform. It authenticates via OAuth2 (authorization code + PKCE) against `inloggen.parnassys.net` and talks to the Parro REST v2 API.

## Commands

```bash
# Install for development
uv sync --extra dev

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_cli.py::TestFmtDate::test_basic

# Run the CLI locally
uv run parro --help

# Install as a tool
uv tool install .
```

## Architecture

Three source modules in `src/parro/`:

- **`client.py`** — OAuth2 authentication (`ParroAuth`) and API client (`ParroClient`). Handles headless login (form submission, no browser), PKCE generation, token persistence at `~/.config/parro/tokens.json` (mode 0600), and token refresh. `ParroClient` is a context manager wrapping `httpx.Client` with methods for each API endpoint (announcements, chatrooms, messages, children, groups, calendar, unread counts). Includes `get_all_announcements()` for cross-group enriched fetching.

- **`helpers.py`** — Pure stdlib helpers reusable outside the CLI: `link_id()` (HAL link ID extraction) and `identity_name()` (display name with surname prefix logic).

- **`cli.py`** — Click-based CLI with 12 commands. Uses Rich for formatted output (panels, tables, icons). Supports `--json` flag for machine-readable output. Credentials come from CLI args, env vars (`PARRO_USERNAME`/`PARRO_PASSWORD`), or interactive prompt. Loads `.env` from `~/.config/parro/.env` and `./env`. Maintains a numbered attachment cache for the `open` command.

`__init__.py` exports `ParroClient`, `ParroAuth`, `link_id`, `identity_name` as the public SDK surface. Core dependency is only `httpx`; CLI extras (`rich`, `click`, `python-dotenv`) are optional via `pip install parro-cli[cli]`.

Entry point: `parro` → `parro.cli:main()` (configured in pyproject.toml).

## Key Patterns

- All HTTP is synchronous via `httpx.Client` (not async)
- OAuth2 flow manually follows redirects and submits HTML forms — no browser involved
- CLI output is Dutch language
- Attachment numbering: announcements/messages display numbered attachments; `parro open <n>` downloads and opens them via the system viewer

# parro-cli

Command-line interface for the Parro school communication platform.

## Installation

```bash
# With uv (recommended)
uv tool install .

# Or with pip
pip install .
```

## Quick start

```bash
# Log in (interactive prompt or use env vars)
parro login

# Show recent announcements across all groups
parro announcements

# Open an attachment by its number from the announcements output
parro open 1
```

## Shell completion

Enable tab completion for your shell:

```bash
# bash (~/.bashrc)
eval "$(parro completion bash)"

# zsh (~/.zshrc)
eval "$(parro completion zsh)"

# fish
parro completion fish > ~/.config/fish/completions/parro.fish
```

## Commands

| Command | Description |
|---------|-------------|
| `parro login` | Authenticate via headless OAuth2 |
| `parro logout` | Remove stored tokens |
| `parro account` | Show account info |
| `parro announcements` | Show announcements (with `--limit`, `--group`) |
| `parro chatrooms` | List chatrooms sorted by activity |
| `parro messages CHATROOM_ID` | Show chat messages (with `--limit`) |
| `parro open REF` | Download and open attachment by number or URL |
| `parro children` | List children |
| `parro groups` | List groups |
| `parro unread` | Show unread counts |
| `parro calendar` | Show iCal URLs |
| `parro completion SHELL` | Output shell completion script |

All data commands support `--json` for JSON output:

```bash
parro --json announcements --limit 5
```

## Configuration

Credentials can be provided via environment variables or `.env` files:

```bash
# Environment variables
export PARRO_USERNAME=you@example.com
export PARRO_PASSWORD=secret

# Or create ~/.config/parro/.env
PARRO_USERNAME=you@example.com
PARRO_PASSWORD=secret
```

The CLI also loads a local `.env` file from the current directory.

Tokens are stored in `~/.config/parro/tokens.json` (mode 0600).

## Development

```bash
uv sync --extra dev
uv run pytest
```

<h1 align="center">
  📬 parro-cli
</h1>

<p align="center">
  <strong>Parro in je terminal.</strong><br>
  Mededelingen lezen, chatrooms volgen en bijlages openen — zonder de app te openen.
</p>

<p align="center">
  <a href="https://github.com/anneschuth/parro-cli"><img alt="GitHub" src="https://img.shields.io/badge/github-anneschuth%2Fparro--cli-blue?logo=github"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776ab?logo=python&logoColor=white">
  <img alt="License MIT" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Version" src="https://img.shields.io/badge/version-0.2.0-orange">
</p>

---

## Wat doet het?

`parro` geeft je toegang tot het [Parro](https://www.parro.com) schoolplatform vanuit de terminal:

- **Mededelingen** lezen met bijlages, direct openen in Preview
- **Chatrooms** bekijken en berichten lezen
- **Ongelezen** aantallen checken
- **Kalender** iCal URLs ophalen
- **JSON output** voor scripting en automatisering

Authenticatie gaat via een headless OAuth2 flow — geen browser nodig.

## Installatie

```bash
# Met uv (aanbevolen)
uv tool install parro-cli

# Vanuit source
git clone https://github.com/anneschuth/parro-cli.git
cd parro-cli
uv tool install .
```

## Snel aan de slag

```bash
# Inloggen
parro login

# Mededelingen bekijken
parro announcements

# Bijlage openen (nummer uit de output)
parro open 3

# Chatrooms
parro chatrooms
parro messages 12345

# Ongelezen berichten
parro unread
```

## Alle commando's

| Commando | Wat het doet |
|---|---|
| `parro login` | Inloggen via headless OAuth2 |
| `parro logout` | Tokens verwijderen |
| `parro account` | Account info tonen |
| `parro announcements` | Mededelingen ophalen (`--limit N`, `--group ID`) |
| `parro chatrooms` | Chatrooms tonen, gesorteerd op activiteit |
| `parro messages <id>` | Berichten in een chatroom (`--limit N`) |
| `parro open <ref>` | Bijlage openen op nummer of URL |
| `parro children` | Kinderen tonen |
| `parro groups` | Groepen tonen |
| `parro unread` | Ongelezen aantallen |
| `parro calendar` | iCal URLs tonen |
| `parro completion <shell>` | Shell completion script genereren |

### JSON output

Elke data-commando ondersteunt `--json` voor machine-leesbare output:

```bash
parro --json announcements --limit 5
parro --json chatrooms | jq '.[0].title'
```

## Configuratie

### Credentials

Drie manieren om in te loggen:

```bash
# 1. Interactief (prompts)
parro login

# 2. Command-line opties
parro login -u je@email.nl -p geheim

# 3. Environment variabelen of .env bestand
export PARRO_USERNAME=je@email.nl
export PARRO_PASSWORD=geheim
parro login
```

Voor `.env` bestanden: plaats ze in `~/.config/parro/.env` of in je huidige directory.

### Tokens

Na het inloggen worden tokens opgeslagen in `~/.config/parro/tokens.json` (mode `0600`). De CLI refresht automatisch verlopen tokens.

## Shell completion

```bash
# bash — toevoegen aan ~/.bashrc
eval "$(parro completion bash)"

# zsh — toevoegen aan ~/.zshrc
eval "$(parro completion zsh)"

# fish
parro completion fish > ~/.config/fish/completions/parro.fish
```

## Development

```bash
git clone https://github.com/anneschuth/parro-cli.git
cd parro-cli
uv sync --extra dev
uv run pytest
uv run parro --help
```

## Licentie

MIT

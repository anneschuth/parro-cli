<h1 align="center">
  📬 parro
</h1>

<p align="center">
  <em>A CLI and Python SDK for Parro, the Dutch school communication platform.</em><br>
  Mededelingen lezen, chatrooms volgen en bijlages openen — zonder de app te openen.
</p>

<p align="center">
  <a href="https://github.com/anneschuth/parro-cli/actions"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/anneschuth/parro-cli/ci.yml?branch=main&label=CI"></a>
  <a href="https://pypi.org/project/parro/"><img alt="PyPI" src="https://img.shields.io/pypi/v/parro"></a>
  <a href="https://pypi.org/project/parro/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/parro"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/anneschuth/parro-cli"></a>
</p>

---

## Wat doet het?

`parro` geeft je toegang tot het [Parro](https://www.parro.com) schoolplatform vanuit de terminal:

- **Mededelingen** lezen met bijlages, direct openen in Preview
- **Chatrooms** bekijken, berichten lezen en zelf berichten sturen
- **Meerdere scholen** naast elkaar, elk met een eigen login
- **Ongelezen** aantallen checken
- **Kalender** iCal URLs ophalen
- **JSON output** voor scripting en automatisering

Authenticatie gaat via een headless OAuth2 flow — geen browser nodig.

## Installatie

```bash
# CLI (met pip)
pip install parro[cli]

# CLI (met uv, aanbevolen)
uv tool install parro[cli]

# CLI (met Homebrew)
brew install anneschuth/tap/parro

# Alleen SDK (geen rich/click)
pip install parro

# Vanuit source
git clone https://github.com/anneschuth/parro-cli.git
cd parro-cli
uv tool install .[cli]
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
parro send 12345 "Kira is vandaag ziek."

# Ongelezen berichten
parro unread
```

## Alle commando's

| Commando | Wat het doet |
|---|---|
| `parro login` | Inloggen via headless OAuth2 |
| `parro logout` | Tokens verwijderen |
| `parro account` | Account info tonen |
| `parro accounts` | Accounts (scholen) van je login tonen |
| `parro announcements` | Mededelingen ophalen (`--limit N`, `--group ID`) |
| `parro chatrooms` | Chatrooms tonen, gesorteerd op activiteit |
| `parro messages <id>` | Berichten in een chatroom (`--limit N`) |
| `parro send <id> [tekst]` | Bericht sturen naar een chatroom (tekst weglaten of `-` = stdin) |
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

### Meerdere accounts op één login

Als je e-mailadres aan meerdere identiteiten gekoppeld is (bijvoorbeeld twee
verzorgers die hetzelfde adres delen), toont ParnaSys na het wachtwoord een
"Account kiezen"-pagina. Dat gebeurt ook als je kinderen op verschillende scholen
zitten: dan staat er per school een account. Standaard wordt het eerste account
gekozen; kies zelf met:

```bash
parro login --account "Jan"          # deel van de getoonde naam (of rol/school)
export PARRO_ACCOUNT=Jan             # of via env
```

Welke accounts je login heeft, zie je met `parro accounts`.

Elk account krijgt zijn eigen tokens, dus je kunt met meerdere scholen tegelijk
ingelogd zijn. Geef bij elk commando aan welk account je bedoelt:

```bash
parro login --account "Regenboog"
parro login --account "Klimop"
parro --account "Regenboog" announcements
parro -a "Klimop" chatrooms
```

Zonder `--account` (en zonder `PARRO_ACCOUNT`) gebruikt de CLI het standaardaccount.

### Tokens

Na het inloggen worden tokens opgeslagen in `~/.config/parro/tokens.json` (mode `0600`); met `--account` in `~/.config/parro/tokens-<account>.json`. De CLI refresht automatisch verlopen tokens. `parro logout` verwijdert alleen de tokens van het gekozen account.

## Shell completion

```bash
# bash — toevoegen aan ~/.bashrc
eval "$(parro completion bash)"

# zsh — toevoegen aan ~/.zshrc
eval "$(parro completion zsh)"

# fish
parro completion fish > ~/.config/fish/completions/parro.fish
```

## SDK gebruik

Het `parro` package kan ook als Python SDK gebruikt worden, zonder CLI-afhankelijkheden:

```python
from parro import ParroClient, ParroAuth, link_id, identity_name

# Inloggen (eenmalig)
tokens = ParroAuth.login("je@email.nl", "geheim")

# API gebruiken
with ParroClient(tokens["access_token"]) as client:
    for ann in client.get_all_announcements(limit=5):
        print(ann["title"], ann.get("_group_name", ""))

    for child in client.get_children():
        print(identity_name(child))

# Meerdere scholen: tokens per account, daarna kiezen met account=...
ParroAuth.login("je@email.nl", "geheim", account="Regenboog")
with ParroClient(account="Regenboog") as client:
    room = client.get_chatrooms()[0]
    client.send_chat_message(link_id(room), "Kira is vandaag ziek.")
```

## Development

```bash
git clone https://github.com/anneschuth/parro-cli.git
cd parro-cli
uv sync --extra dev
uv run pre-commit install
uv run pytest
uv run parro --help
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## Bijdragen

Pull requests zijn welkom. Draai `uv run pytest`, `uv run ruff check .` en `uv run ty check` voordat je een PR opent; de CI doet hetzelfde.

Met dank aan [@mingoes](https://github.com/mingoes) (login-fix na de IDP-wijziging en de accountkeuze) en [@wienke](https://github.com/wienke) (paginering via Range-headers, Rich-escaping en de afkapbug in mededelingen).

## Licentie

MIT — see [LICENSE](LICENSE).

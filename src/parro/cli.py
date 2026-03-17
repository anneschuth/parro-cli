"""Parro CLI - command-line interface for the Parro school platform.

Usage:
    parro login                          # Authenticate via browser
    parro announcements [--limit N]      # Show announcements
    parro chatrooms                      # List chat rooms
    parro messages CHATROOM_ID           # Show messages in a chatroom
    parro children                       # List children
    parro groups                         # List groups
    parro unread                         # Show unread counts
    parro calendar                       # Show calendar iCal URLs
    parro account                        # Show account info
    parro open REF                       # Open attachment by number or URL
    parro completion SHELL               # Output shell completion script
"""

from __future__ import annotations

__version__ = "0.3.0"

import json
import sys
from datetime import datetime
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .client import ParroAuth, ParroClient
from .helpers import identity_name as _identity_name
from .helpers import link_id as _link_id

console = Console()


_last_attachment_urls: list[str] = []
_LAST_URLS_PATH = Path("~/.config/parro/.last_attachments").expanduser()


def _save_attachment_urls(urls: list[str]) -> None:
    """Save attachment URLs so `parro open <n>` can use them."""
    _LAST_URLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LAST_URLS_PATH.write_text("\n".join(urls))


def _load_attachment_urls() -> list[str]:
    if _LAST_URLS_PATH.exists():
        return [u for u in _LAST_URLS_PATH.read_text().splitlines() if u]
    return []


def _fmt_date(iso: str) -> str:
    """Format ISO datetime to readable Dutch format."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d %b %H:%M")
    except (ValueError, TypeError):
        return iso[:16]


def _print_announcements(items: list[dict], as_json: bool):
    if as_json:
        print(json.dumps(items, indent=2, default=str))
        return

    if not items:
        console.print("[dim]Geen mededelingen gevonden[/]")
        return

    for ann in items:
        title = ann.get("title", "(geen titel)")
        contents = ann.get("contents", "")
        created = _fmt_date(ann.get("createdAt", ""))
        read = ann.get("read", False)
        owner = ann.get("owner", {})
        owner_name = _identity_name(owner)
        attachments = ann.get("attachments", [])
        group_name = ann.get("_group_name", "")

        read_icon = "[dim]●[/]" if read else "[bold red]●[/]"
        header = f"{read_icon} [bold]{title}[/]"
        meta_parts = []
        if group_name:
            meta_parts.append(f"[cyan]{group_name}[/cyan]")
        meta_parts.append(f"Van: {owner_name}")
        meta_parts.append(created)
        if attachments:
            meta_parts.append(f"{len(attachments)} bijlage(n)")
        meta = " | ".join(meta_parts)

        # Build attachment links with index numbers
        att_lines = ""
        for att in attachments:
            atype = att.get("attachmentType", "").lower()
            icon = {"image": "img", "pdf": "pdf", "document": "doc"}.get(atype, "file")
            for entry in att.get("entries", []):
                url = entry.get("url", "")
                size = entry.get("size", 0)
                etype = entry.get("type", "")
                if url and etype == "SOURCE":
                    _last_attachment_urls.append(url)
                    idx = len(_last_attachment_urls)
                    size_str = f" ({size // 1024}KB)" if size else ""
                    filename = url.split("/")[-1]
                    att_lines += (
                        f"\n  [dim]\\[{idx}][/dim] [{icon}]"
                        f" [link={url}]{filename}[/link]{size_str}"
                    )
                    break

        body = f"{meta}\n\n{contents[:500]}"
        if att_lines:
            body += f"\n{att_lines}"

        console.print(
            Panel(
                body,
                title=header,
                border_style="blue" if read else "red",
            )
        )
        console.print()

    # Save attachment URLs for `parro open <n>`
    if _last_attachment_urls:
        _save_attachment_urls(_last_attachment_urls)


class AliasedGroup(click.Group):
    """Click group that handles errors gracefully."""

    pass


@click.group(cls=AliasedGroup)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output als JSON")
@click.version_option(version=__version__, prog_name="parro")
@click.pass_context
def cli(ctx, as_json):
    """Parro CLI - toegang tot het Parro schoolplatform vanuit de terminal."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json


@cli.command()
@click.option("-u", "--username", default=None, help="Email (of PARRO_USERNAME env)")
@click.option("-p", "--password", default=None, help="Wachtwoord (of PARRO_PASSWORD env)")
@click.option(
    "--store", is_flag=True, default=False, help="Credentials opslaan in ~/.config/parro/.env"
)
def login(username, password, store):
    """Inloggen bij Parro via headless OAuth2 flow."""
    import os

    from dotenv import load_dotenv

    from .client import TOKEN_PATH

    # Load .env files: ~/.config/parro/.env first, then local .env
    env_path = TOKEN_PATH.parent / ".env"
    load_dotenv(env_path)
    load_dotenv()  # local .env

    username = username or os.environ.get("PARRO_USERNAME", "")
    password = password or os.environ.get("PARRO_PASSWORD", "")

    try:
        tokens = ParroAuth.login(username=username or None, password=password or None)
        console.print("[green]Login geslaagd![/]")
        # Show account info
        with ParroClient(tokens["access_token"]) as client:
            account = client.get_account()
            email = account.get("email", "")
            console.print(f"  Email: {email}")

        if store and username and password:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text(f"PARRO_USERNAME={username}\nPARRO_PASSWORD={password}\n")
            env_path.chmod(0o600)
            console.print(f"  [dim]Credentials opgeslagen in {env_path}[/]")
    except Exception as e:
        console.print(f"[red]Login mislukt: {e}[/]")
        sys.exit(1)


@cli.command()
def logout():
    """Uitloggen (tokens verwijderen)."""
    from .client import TOKEN_PATH

    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        console.print("[green]Uitgelogd.[/]")
    else:
        console.print("[dim]Je was al uitgelogd.[/]")


@cli.command()
@click.pass_context
def account(ctx):
    """Account info tonen."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        data = client.get_account()
        if as_json:
            print(json.dumps(data, indent=2, default=str))
            return
        console.print(
            Panel(
                f"Email: {data.get('email', '')}\n"
                f"Username: {data.get('externalUsername', '')}\n"
                f"ID: {_link_id(data)}",
                title="[bold]Parro Account[/]",
                border_style="blue",
            )
        )


@cli.command()
@click.option("--limit", default=20, type=int, help="Maximum aantal mededelingen")
@click.option("--group", default=None, type=int, help="Filter op groep ID")
@click.pass_context
def announcements(ctx, limit, group):
    """Mededelingen ophalen."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        if group:
            # Single group
            items = client.get_announcements(group_id=group)
            _print_announcements(items[:limit], as_json)
        else:
            items = client.get_all_announcements(limit=limit)
            _print_announcements(items, as_json)


@cli.command()
@click.pass_context
def chatrooms(ctx):
    """Chatrooms tonen, gesorteerd op activiteit."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        items = client.get_chatrooms()

        if as_json:
            print(json.dumps(items, indent=2, default=str))
            return

        if not items:
            console.print("[dim]Geen chatrooms gevonden[/]")
            return

        table = Table(title="Chatrooms")
        table.add_column("ID", style="dim")
        table.add_column("Naam", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Laatste", style="dim")
        table.add_column("Ongelezen", style="red")

        # Sort by most recent activity
        sorted_items = sorted(items, key=lambda r: r.get("sortDate", ""), reverse=True)
        for room in sorted_items:
            room_id = str(_link_id(room) or "")
            name = room.get("title", room.get("subject", room.get("name", "")))
            room_type = room.get("type", "")
            last = _fmt_date(room.get("sortDate", ""))
            unread = str(room.get("unreadCount", 0))
            table.add_row(room_id, name, room_type, last, unread)

        console.print(table)


@cli.command()
@click.argument("chatroom_id", type=int)
@click.option("--limit", default=50, type=int, help="Maximum aantal berichten")
@click.pass_context
def messages(ctx, chatroom_id, limit):
    """Berichten in een chatroom tonen."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        items = client.get_chat_messages(chatroom_id)

        if as_json:
            print(json.dumps(items[:limit], indent=2, default=str))
            return

        if not items:
            console.print("[dim]Geen berichten gevonden[/]")
            return

        for msg in reversed(items[:limit]):
            identity = msg.get("identity", {})
            sender = _identity_name(identity)
            text = msg.get("text", msg.get("contents", ""))
            created = _fmt_date(msg.get("lastModifiedAt", ""))
            if not text:
                text = "[dim]\\[media][/dim]"

            console.print(f"  [dim]{created}[/] [bold]{sender}:[/] {text}")


@click.command("open")
@click.argument("ref", type=str)
def open_attachment(ref):
    """Open een bijlage in Preview/standaard app.

    REF is een nummer (uit announcements output) of een URL.
    """
    import subprocess
    import tempfile

    # Check if it's a number referencing a previous attachment
    if ref.isdigit():
        idx = int(ref)
        urls = _load_attachment_urls()
        if not urls:
            console.print("[red]Geen bijlages gevonden. Run eerst `parro announcements`.[/]")
            sys.exit(1)
        if idx < 1 or idx > len(urls):
            console.print(f"[red]Nummer {idx} bestaat niet. Beschikbaar: 1-{len(urls)}[/]")
            sys.exit(1)
        url = urls[idx - 1]
    else:
        url = ref

    filename = url.split("/")[-1].split("?")[0]

    console.print(f"  Downloaden: {filename}...", end="")
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()

    tmp = Path(tempfile.gettempdir()) / f"parro-{filename}"
    tmp.write_bytes(resp.content)

    console.print(f" [green]ok[/green] ({len(resp.content) // 1024}KB)")
    subprocess.run(["open", str(tmp)])


# Register the "open" command
cli.add_command(open_attachment)


@cli.command()
@click.pass_context
def children(ctx):
    """Kinderen tonen."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        items = client.get_children()

        if as_json:
            print(json.dumps(items, indent=2, default=str))
            return

        if not items:
            console.print("[dim]Geen kinderen gevonden[/]")
            return

        for child in items:
            name = _identity_name(child)
            child_id = _link_id(child)
            if name:
                console.print(f"  [bold]{name}[/] (ID: {child_id})")


@cli.command()
@click.pass_context
def groups(ctx):
    """Groepen tonen."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        items = client.get_groups()

        if as_json:
            print(json.dumps(items, indent=2, default=str))
            return

        if not items:
            console.print("[dim]Geen groepen gevonden[/]")
            return

        table = Table(title="Groepen")
        table.add_column("ID", style="dim")
        table.add_column("Naam", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Ongelezen", style="red")
        table.add_column("Leerlingen", style="green")

        for g in items:
            gid = str(_link_id(g) or "")
            name = g.get("name", "")
            gtype = g.get("type", "")
            unread = str(g.get("unreadCount", 0))
            children_count = str(g.get("numberOfChildren", 0))
            table.add_row(gid, name, gtype, unread, children_count)

        console.print(table)


@cli.command()
@click.pass_context
def unread(ctx):
    """Ongelezen aantallen tonen."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        items = client.get_unread_counts()

        if as_json:
            print(json.dumps(items, indent=2, default=str))
            return

        for item in items:
            ann = item.get("numberOfUnreadAnnouncements", 0)
            cal = item.get("numberOfUnreadCalendarItems", 0)
            chat = item.get("numberOfUnreadChatRooms", 0)
            news = item.get("numberOfUnreadSystemNewsItems", 0)

            console.print(f"  Mededelingen: [bold]{ann}[/] ongelezen")
            console.print(f"  Kalender:     [bold]{cal}[/] ongelezen")
            console.print(f"  Chatrooms:    [bold]{chat}[/] ongelezen")
            console.print(f"  Parro nieuws: [bold]{news}[/] ongelezen")


@cli.command()
@click.pass_context
def calendar(ctx):
    """Kalender iCal URLs tonen."""
    as_json = ctx.obj["json"]
    with ParroClient() as client:
        urls = client.get_calendar_urls()

        if as_json:
            print(json.dumps(urls, indent=2))
            return

        if not urls:
            console.print("[dim]Geen kalender-URLs gevonden[/]")
            return

        for url in urls:
            console.print(f"  [link={url}]{url}[/link]")


@cli.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell):
    """Output shell completion script.

    Add to your shell config to enable tab completion:

    \b
      # bash (~/.bashrc)
      eval "$(parro completion bash)"

    \b
      # zsh (~/.zshrc)
      eval "$(parro completion zsh)"

    \b
      # fish (~/.config/fish/completions/parro.fish)
      parro completion fish > ~/.config/fish/completions/parro.fish
    """
    import os

    os.environ["_PARRO_COMPLETE"] = f"{shell}_source"
    try:
        cli.main(standalone_mode=False)
    except SystemExit:
        pass
    finally:
        del os.environ["_PARRO_COMPLETE"]


def main():
    try:
        cli(standalone_mode=True)
    except RuntimeError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Sessie verlopen. Run `parro login` opnieuw.[/]")
        else:
            console.print(f"[red]API fout: {e.response.status_code}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()

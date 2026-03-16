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
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .client import ParroClient, ParroAuth

console = Console()


def _link_id(item: dict, rel: str = "self") -> int | None:
    for link in item.get("links", []):
        if link.get("rel") == rel:
            return link.get("id")
    return None


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


def _identity_name(identity: dict) -> str:
    """Extract display name from an identity object."""
    name = identity.get("displayName", "")
    if not name:
        first = identity.get("firstName", "")
        prefix = identity.get("surnamePrefix", "")
        last = identity.get("surname", "")
        parts = [first, prefix, last] if prefix else [first, last]
        name = " ".join(p for p in parts if p)
    return name or "Onbekend"


def cmd_login(args):
    """Authenticate via headless OAuth2 flow."""
    import os

    from dotenv import load_dotenv

    from .client import TOKEN_PATH

    # Load .env files: ~/.config/parro/.env first, then local .env
    load_dotenv(TOKEN_PATH.parent / ".env")
    load_dotenv()  # local .env

    username = args.username or os.environ.get("PARRO_USERNAME", "")
    password = args.password or os.environ.get("PARRO_PASSWORD", "")

    try:
        tokens = ParroAuth.login(username=username or None, password=password or None)
        console.print("[green]Login geslaagd![/]")
        # Show account info
        with ParroClient(tokens["access_token"]) as client:
            account = client.get_account()
            email = account.get("email", "")
            console.print(f"  Email: {email}")
    except Exception as e:
        console.print(f"[red]Login mislukt: {e}[/]")
        sys.exit(1)


def cmd_logout(args):
    """Remove stored tokens."""
    from .client import TOKEN_PATH

    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        console.print("[green]Uitgelogd.[/]")
    else:
        console.print("[dim]Je was al uitgelogd.[/]")


def cmd_account(args):
    """Show account info."""
    with ParroClient() as client:
        account = client.get_account()
        if args.json:
            print(json.dumps(account, indent=2, default=str))
            return
        console.print(Panel(
            f"Email: {account.get('email', '')}\n"
            f"Username: {account.get('externalUsername', '')}\n"
            f"ID: {_link_id(account)}",
            title="[bold]Parro Account[/]",
            border_style="blue",
        ))


def cmd_announcements(args):
    """Show announcements."""
    with ParroClient() as client:
        if args.group:
            # Single group
            items = client.get_announcements(group_id=args.group)
            _print_announcements(items[:args.limit], args)
        else:
            # All groups — fetch per group so we can show the group name
            groups = client.get_groups()
            all_items = []
            for group in groups:
                gid = _link_id(group)
                gname = group.get("name", "")
                items = client.get_announcements(group_id=gid)
                for item in items:
                    item["_group_name"] = gname
                all_items.extend(items)

            # Sort by date
            all_items.sort(key=lambda a: a.get("sortDate", ""))
            _print_announcements(all_items[-args.limit:], args)


def _print_announcements(items: list[dict], args):
    if args.json:
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
                    att_lines += f"\n  [dim]\\[{idx}][/dim] [{icon}] [link={url}]{filename}[/link]{size_str}"
                    break

        body = f"{meta}\n\n{contents[:500]}"
        if att_lines:
            body += f"\n{att_lines}"

        console.print(Panel(
            body,
            title=header,
            border_style="blue" if read else "red",
        ))
        console.print()

    # Save attachment URLs for `parro open <n>`
    if _last_attachment_urls:
        _save_attachment_urls(_last_attachment_urls)


def cmd_chatrooms(args):
    """List chat rooms."""
    with ParroClient() as client:
        items = client.get_chatrooms()

        if args.json:
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
        sorted_items = sorted(
            items, key=lambda r: r.get("sortDate", ""), reverse=True
        )
        for room in sorted_items:
            room_id = str(_link_id(room) or "")
            name = room.get("title", room.get("subject", room.get("name", "")))
            room_type = room.get("type", "")
            last = _fmt_date(room.get("sortDate", ""))
            unread = str(room.get("unreadCount", 0))
            table.add_row(room_id, name, room_type, last, unread)

        console.print(table)


def cmd_messages(args):
    """Show messages in a chatroom."""
    with ParroClient() as client:
        items = client.get_chat_messages(args.chatroom_id)

        if args.json:
            print(json.dumps(items[:args.limit], indent=2, default=str))
            return

        if not items:
            console.print("[dim]Geen berichten gevonden[/]")
            return

        for msg in reversed(items[:args.limit]):
            identity = msg.get("identity", {})
            sender = _identity_name(identity)
            text = msg.get("text", msg.get("contents", ""))
            created = _fmt_date(msg.get("lastModifiedAt", ""))
            dtype = msg.get("dtype", "")

            if not text:
                text = "[dim]\\[media][/dim]"

            console.print(f"  [dim]{created}[/] [bold]{sender}:[/] {text}")


def cmd_children(args):
    """List children."""
    with ParroClient() as client:
        items = client.get_children()

        if args.json:
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


def cmd_groups(args):
    """List groups."""
    with ParroClient() as client:
        items = client.get_groups()

        if args.json:
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

        for group in items:
            gid = str(_link_id(group) or "")
            name = group.get("name", "")
            gtype = group.get("type", "")
            unread = str(group.get("unreadCount", 0))
            children = str(group.get("numberOfChildren", 0))
            table.add_row(gid, name, gtype, unread, children)

        console.print(table)


def cmd_unread(args):
    """Show unread counts."""
    with ParroClient() as client:
        items = client.get_unread_counts()

        if args.json:
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


def cmd_open(args):
    """Download and open an attachment in the default app.

    Accepts a URL or a number from the last `parro announcements` output.
    """
    import subprocess
    import tempfile

    ref = args.ref

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


def cmd_calendar(args):
    """Show calendar iCal URLs."""
    with ParroClient() as client:
        urls = client.get_calendar_urls()

        if args.json:
            print(json.dumps(urls, indent=2))
            return

        if not urls:
            console.print("[dim]Geen kalender-URLs gevonden[/]")
            return

        for url in urls:
            console.print(f"  [link={url}]{url}[/link]")


def main():
    parser = argparse.ArgumentParser(
        description="Parro CLI - toegang tot het Parro schoolplatform vanuit de terminal",
    )
    parser.add_argument("--json", action="store_true", help="Output als JSON")

    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="Inloggen bij Parro")
    login_parser.add_argument("-u", "--username", help="Email (of PARRO_USERNAME env)")
    login_parser.add_argument("-p", "--password", help="Wachtwoord (of PARRO_PASSWORD env)")
    subparsers.add_parser("logout", help="Uitloggen (tokens verwijderen)")
    subparsers.add_parser("account", help="Account info tonen")

    ann_parser = subparsers.add_parser("announcements", help="Mededelingen ophalen")
    ann_parser.add_argument("--limit", type=int, default=20)
    ann_parser.add_argument("--group", type=int, help="Filter op groep ID")

    subparsers.add_parser("chatrooms", help="Chatrooms tonen")

    msg_parser = subparsers.add_parser("messages", help="Berichten in een chatroom")
    msg_parser.add_argument("chatroom_id", type=int)
    msg_parser.add_argument("--limit", type=int, default=50)

    open_parser = subparsers.add_parser("open", help="Open een bijlage in Preview/standaard app")
    open_parser.add_argument("ref", help="Nummer (uit announcements) of URL")

    subparsers.add_parser("children", help="Kinderen tonen")
    subparsers.add_parser("groups", help="Groepen tonen")
    subparsers.add_parser("unread", help="Ongelezen aantallen")
    subparsers.add_parser("calendar", help="Kalender iCal URLs")

    args = parser.parse_args()

    commands = {
        "login": cmd_login,
        "logout": cmd_logout,
        "account": cmd_account,
        "announcements": cmd_announcements,
        "chatrooms": cmd_chatrooms,
        "messages": cmd_messages,
        "open": cmd_open,
        "children": cmd_children,
        "groups": cmd_groups,
        "unread": cmd_unread,
        "calendar": cmd_calendar,
    }

    try:
        commands[args.command](args)
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

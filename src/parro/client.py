"""Parro API client - real implementation using rest-v2.parro.com.

Authentication uses OAuth2 authorization code flow with PKCE via
inloggen.parnassys.net. The login flow is done headlessly via httpx
(no browser needed). Tokens are stored locally and refreshed automatically.
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import json
import re
import secrets
import urllib.parse
from pathlib import Path
from types import TracebackType
from typing import Any

import httpx

# API endpoints
REST_API = "https://rest-v2.parro.com/rest/v2"

# OAuth2 configuration
IDP_BASE = "https://inloggen.parnassys.net"
AUTHORIZE_URL = f"{IDP_BASE}/idp/oauth2/authorize"
TOKEN_URL = f"{IDP_BASE}/idp/oauth2/token"
CLIENT_ID = "W52dbSBQuFp-LF4Xch1r"
REDIRECT_URI = "parro://oauth2"

# Token storage
TOKEN_PATH = Path("~/.config/parro/tokens.json").expanduser()


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _save_tokens(data: dict[str, str]) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(data, indent=2))
    TOKEN_PATH.chmod(0o600)


def _load_tokens() -> dict[str, str] | None:
    if TOKEN_PATH.exists():
        try:
            return json.loads(TOKEN_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _login_field_names(html: str) -> tuple[str, str]:
    """Find the username/password input names on the IDP login form.

    ParnaSys has renamed these before (``e-mailadres`` → ``emailadres``), so
    read them from the page instead of hard-coding; fall back to the current
    known names when the form can't be parsed.
    """
    user_field, pass_field = "emailadres", "wachtwoord"
    for tag in re.findall(r"<input[^>]*>", html, re.IGNORECASE):
        type_match = re.search(r'type="([^"]*)"', tag, re.IGNORECASE)
        name_match = re.search(r'name="([^"]*)"', tag, re.IGNORECASE)
        if not name_match:
            continue
        itype = (type_match.group(1) if type_match else "text").lower()
        if itype == "password":
            pass_field = name_match.group(1)
        elif itype in ("text", "email") and "password" not in name_match.group(1).lower():
            user_field = name_match.group(1)
    return user_field, pass_field


def _parse_account_chooser(html: str) -> list[dict[str, str]]:
    """Parse the IDP's "Account kiezen" page.

    When one login is linked to several identities (e.g. two guardians sharing
    an e-mail address) the IDP shows an account list after the password. Each
    entry is a Wicket-Ajax link; returns ``[{"name", "role", "url", "focus_id"}]``
    in page order. Empty list when the page is not an account chooser.
    """
    links = dict(
        re.findall(
            r'"u":"([^"]*accountKeuze-accounts-account-\d+)","c":"([^"]+)"',
            html,
        )
    )
    accounts: list[dict[str, str]] = []
    for url, focus_id in links.items():
        item = re.search(rf'<li[^>]*id="{re.escape(focus_id)}"[^>]*>(.*?)</li>', html, re.DOTALL)
        text = item.group(1) if item else ""
        name_block = re.search(r'account-list__name"[^>]*>(.*?)</span>\s*</span>', text, re.DOTALL)
        role_block = re.search(r'account-list__role"[^>]*>(.*?)</span>\s*</span>', text, re.DOTALL)

        def _clean(block: re.Match[str] | None) -> str:
            raw = re.sub(r"<[^>]+>", " ", block.group(1)) if block else ""
            return re.sub(r"\s+", " ", raw).strip()

        accounts.append(
            {
                "name": _clean(name_block),
                "role": _clean(role_block),
                "url": url,
                "focus_id": focus_id,
            }
        )
    return accounts


def _choose_account(client: httpx.Client, page_url: str, html: str, account: str | None) -> str:
    """Pick an entry on the account chooser and return the redirect it yields.

    *account* is a case-insensitive substring of the displayed name (or role);
    ``None`` picks the first entry. The click is a Wicket-Ajax GET whose
    reply carries the next location in the ``Ajax-Location`` header or an
    ``<ajax-response><redirect>`` body.
    """
    accounts = _parse_account_chooser(html)
    if not accounts:
        raise RuntimeError("Accountkeuze-pagina gevonden maar geen accounts herkend.")

    chosen = accounts[0]
    if account:
        wanted = account.lower()
        matches = [
            a for a in accounts if wanted in a["name"].lower() or wanted in a["role"].lower()
        ]
        if not matches:
            names = ", ".join(f"{a['name']} ({a['role']})" for a in accounts)
            raise RuntimeError(f"Account '{account}' niet gevonden. Beschikbaar: {names}")
        chosen = matches[0]

    base_match = re.search(r'Wicket\.Ajax\.baseUrl="([^"]*)"', html)
    base_url = base_match.group(1) if base_match else urllib.parse.urlparse(page_url).path
    resp = client.get(
        urllib.parse.urljoin(page_url, chosen["url"]),
        headers={
            "Wicket-Ajax": "true",
            "Wicket-Ajax-BaseURL": base_url,
            "Wicket-FocusedElementId": chosen["focus_id"],
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    location = resp.headers.get("ajax-location", "")
    if not location:
        redirect_match = re.search(r"<redirect><!\[CDATA\[(.*?)\]\]></redirect>", resp.text)
        location = redirect_match.group(1) if redirect_match else ""
    if not location:
        raise RuntimeError(
            f"Accountkeuze voor '{chosen['name']}' gaf geen redirect (HTTP {resp.status_code})."
        )
    return location


class ParroAuth:
    """Handle OAuth2 authentication for Parro."""

    @staticmethod
    def login(
        username: str | None = None,
        password: str | None = None,
        account: str | None = None,
    ) -> dict[str, str]:
        """Log in to Parro via headless OAuth2 flow.

        Performs the full authorization code + PKCE flow by:
        1. Starting the OAuth authorize request
        2. Posting credentials to the IDP login form
        3. Picking an identity if the IDP shows an account chooser
           (*account* = substring of the shown name; default: first entry)
        4. Following redirects until we get the auth code
        5. Exchanging the code for tokens

        No browser needed.
        """
        if not username:
            username = input("Parro email: ")
        if not password:
            password = getpass.getpass("Parro wachtwoord: ")

        verifier, challenge = _generate_pkce()
        state = secrets.token_urlsafe(32)

        auth_params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "openid",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        with httpx.Client(
            follow_redirects=False,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh) Parro-CLI/0.1"},
        ) as client:
            # Step 1: Hit the authorize endpoint — get redirected to login page
            resp = client.get(AUTHORIZE_URL, params=auth_params)

            # Follow redirects manually (to collect cookies)
            while resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers["location"]
                if not location.startswith("http"):
                    location = f"{IDP_BASE}{location}"
                resp = client.get(location)

            # Step 2: We should now be on the login page.
            # Find the login form action URL and any hidden fields.
            html = resp.text
            action_match = re.search(r'<form[^>]*action="([^"]*)"', html, re.IGNORECASE)
            if not action_match:
                raise RuntimeError(
                    "Kon het login formulier niet vinden. Mogelijk is de IDP interface veranderd."
                )

            form_action = action_match.group(1).replace("&amp;", "&")
            if form_action.startswith("./"):
                # Relative to current page path
                base_path = str(resp.url).split("?")[0]
                if not base_path.endswith("/"):
                    base_path = base_path.rsplit("/", 1)[0] + "/"
                form_action = base_path + form_action[2:]
            elif not form_action.startswith("http"):
                form_action = f"{IDP_BASE}{form_action}"

            # Extract hidden form fields
            form_data = {}
            for match in re.finditer(
                r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"',
                html,
                re.IGNORECASE,
            ):
                form_data[match.group(1)] = match.group(2)

            # Also check reverse order (value before name)
            for match in re.finditer(
                r'<input[^>]*value="([^"]*)"[^>]*type="hidden"[^>]*name="([^"]*)"',
                html,
                re.IGNORECASE,
            ):
                form_data[match.group(2)] = match.group(1)

            # Add credentials — field names are read from the form because
            # ParnaSys has renamed them before (e-mailadres → emailadres)
            user_field, pass_field = _login_field_names(html)
            form_data[user_field] = username
            form_data[pass_field] = password
            # Wicket requires the submit button name to be present
            form_data["aanmelden"] = "x"

            # Step 3: Submit the login form
            resp = client.post(
                form_action,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Step 4: Follow redirects until we hit parro://oauth2?code=...
            max_redirects = 20
            for _ in range(max_redirects):
                if resp.status_code not in (301, 302, 303, 307, 308):
                    # Several identities on one login → "Account kiezen" page
                    if "accountKeuze" in resp.text:
                        location = _choose_account(client, str(resp.url), resp.text, account)
                        if location.startswith("parro://"):
                            resp = httpx.Response(302, headers={"location": location})
                            continue
                        if not location.startswith("http"):
                            location = urllib.parse.urljoin(str(resp.url), location)
                        resp = client.get(location)
                        continue
                    # Check if we're on an error page
                    if "error" in resp.text.lower() and "password" in resp.text.lower():
                        raise RuntimeError("Login mislukt: onjuist wachtwoord of gebruikersnaam.")
                    # Maybe there's a "choose application" page
                    if "kies_applicatie" in resp.url.path:
                        # Click on Parro — find the link
                        parro_match = re.search(
                            r'href="([^"]*)"[^>]*>.*?Parro',
                            resp.text,
                            re.IGNORECASE | re.DOTALL,
                        )
                        if parro_match:
                            link = parro_match.group(1)
                            if not link.startswith("http"):
                                link = f"{IDP_BASE}{link}"
                            resp = client.get(link)
                            continue
                    break

                location = resp.headers.get("location", "")

                # Check for the parro:// redirect with code
                if location.startswith("parro://"):
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
                    if "code" in qs:
                        code = qs["code"][0]
                        # Exchange for tokens
                        token_resp = client.post(
                            TOKEN_URL,
                            data={
                                "grant_type": "authorization_code",
                                "client_id": CLIENT_ID,
                                "code": code,
                                "redirect_uri": REDIRECT_URI,
                                "code_verifier": verifier,
                            },
                        )
                        token_resp.raise_for_status()
                        tokens = token_resp.json()
                        if "access_token" not in tokens:
                            raise RuntimeError(f"Token exchange mislukt: {tokens}")
                        _save_tokens(tokens)
                        return tokens

                    if "error" in qs:
                        raise RuntimeError(
                            f"Login mislukt: {qs.get('error_description', qs['error'])}"
                        )

                # Follow the redirect
                if not location.startswith("http"):
                    location = f"{IDP_BASE}{location}"
                resp = client.get(location)

            raise RuntimeError(
                "Login mislukt: kon geen authorization code verkrijgen. "
                "Controleer je inloggegevens."
            )

    @staticmethod
    def refresh(refresh_token: str) -> dict[str, str]:
        """Refresh the access token."""
        resp = httpx.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": refresh_token,
            },
            timeout=30,
        )
        resp.raise_for_status()
        tokens = resp.json()
        if "access_token" in tokens:
            _save_tokens(tokens)
        return tokens

    @staticmethod
    def get_token() -> str | None:
        """Get a valid access token, refreshing if needed."""
        tokens = _load_tokens()
        if not tokens:
            return None

        access_token = tokens.get("access_token", "")
        if access_token:
            try:
                resp = httpx.get(
                    f"{REST_API}/account/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return access_token
            except httpx.HTTPError:
                pass

        refresh_token = tokens.get("refresh_token", "")
        if refresh_token:
            try:
                new_tokens = ParroAuth.refresh(refresh_token)
                return new_tokens.get("access_token")
            except Exception:
                pass

        return None


class ParroClient:
    """Synchronous Parro API client using the real REST v2 API."""

    def __init__(self, token: str | None = None):
        self.token = token
        self._client: httpx.Client | None = None

    def __enter__(self) -> ParroClient:
        if not self.token:
            self.token = ParroAuth.get_token()
        if not self.token:
            raise RuntimeError("Not authenticated. Run `parro login` first.")
        self._client = httpx.Client(
            base_url=REST_API,
            timeout=30,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client:
            self._client.close()

    def _get(self, path: str, **params: Any) -> Any:
        assert self._client is not None
        resp = self._client.get(path, params=params or None)
        resp.raise_for_status()
        return resp.json()

    def _items(self, path: str, **params: Any) -> list[dict[str, Any]]:
        data = self._get(path, **params)
        if isinstance(data, dict):
            return data.get("items", [])
        return data if isinstance(data, list) else []

    def _items_paged(self, path: str, limit: int, **params: Any) -> list[dict[str, Any]]:
        """Fetch up to *limit* items, paging with HTTP ``Range`` headers.

        The API serves at most 100 items per response and ignores query
        paging parameters; the rest of a collection is exposed via HTTP
        ``Range`` headers (responses carry ``Content-Range: items 0-99/…``).
        Pages are fetched until *limit* items are collected or the
        collection runs out. The total in ``Content-Range`` is unreliable,
        so a short, empty, or 416 response ends the loop instead.
        """
        assert self._client is not None
        page_size = 100
        items: list[dict[str, Any]] = []
        while len(items) < limit:
            start = len(items)
            resp = self._client.get(
                path,
                params=params or None,
                headers={"Range": f"items={start}-{start + page_size - 1}"},
            )
            if resp.status_code == 416:  # asked past the end of the collection
                break
            resp.raise_for_status()
            data = resp.json()
            page = data.get("items", []) if isinstance(data, dict) else []
            if not page:
                break
            items.extend(page)
            if len(page) < page_size:
                break
        return items[:limit]

    def get_account(self) -> dict[str, Any]:
        return self._get("/account/me")

    def get_children(self) -> list[dict[str, Any]]:
        return self._items("/child")

    def get_groups(self, scope: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"dtype": "identity.RHomeGroup"}
        if scope:
            params["scope"] = scope
        return self._items("/group", **params)

    def get_announcements(
        self, group_id: int | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch announcements, newest first.

        With *limit* set, pages with HTTP ``Range`` headers until *limit*
        announcements are collected or history runs out. ``None`` keeps the
        single-request behaviour (the newest page only, at most 100).
        """
        params: dict[str, Any] = {"dtype": "event.RAnnouncementEvent"}
        if group_id:
            params["group"] = group_id
        if limit is None:
            return self._items("/event", **params)
        return self._items_paged("/event", limit, **params)

    def get_chatrooms(self) -> list[dict[str, Any]]:
        return self._items("/chatroom")

    def get_chat_messages(
        self, chatroom_id: int, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch chat messages, newest first.

        With *limit* set, pages with HTTP ``Range`` headers until *limit*
        messages are collected or history runs out. ``None`` keeps the
        single-request behaviour (the newest page only, at most 100).
        """
        path = f"/chatroom/{chatroom_id}/chatmessage"
        if limit is None:
            return self._items(path)
        return self._items_paged(path, limit)

    def get_calendar_urls(self) -> list[str]:
        data = self._get("/calendar/sync")
        return data.get("strings", [])

    def get_unread_counts(self) -> list[dict[str, Any]]:
        return self._items("/identity/unreadcounts")

    def get_all_announcements(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetch announcements across all groups, enriched with group name.

        Each announcement dict gets a ``_group_name`` key.  Results are
        sorted by ``sortDate`` ascending.  When *limit* is given only the
        last *limit* items are returned.
        """
        from .helpers import link_id

        groups = self.get_groups()
        all_items: list[dict] = []
        for g in groups:
            gid = link_id(g)
            gname = g.get("name", "")
            items = self.get_announcements(group_id=gid, limit=limit)
            for item in items:
                item["_group_name"] = gname
            all_items.extend(items)

        all_items.sort(key=lambda a: a.get("sortDate", ""))
        if limit is not None:
            all_items = all_items[-limit:]
        return all_items

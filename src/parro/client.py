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


def _save_tokens(data: dict) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(data, indent=2))
    TOKEN_PATH.chmod(0o600)


def _load_tokens() -> dict | None:
    if TOKEN_PATH.exists():
        try:
            return json.loads(TOKEN_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


class ParroAuth:
    """Handle OAuth2 authentication for Parro."""

    @staticmethod
    def login(username: str | None = None, password: str | None = None) -> dict:
        """Log in to Parro via headless OAuth2 flow.

        Performs the full authorization code + PKCE flow by:
        1. Starting the OAuth authorize request
        2. Posting credentials to the IDP login form
        3. Following redirects until we get the auth code
        4. Exchanging the code for tokens

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

            # Add credentials — ParnaSys uses Dutch field names
            form_data["e-mailadres"] = username
            form_data["wachtwoord"] = password
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
    def refresh(refresh_token: str) -> dict:
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

    def __enter__(self):
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

    def __exit__(self, *exc):
        if self._client:
            self._client.close()

    def _get(self, path: str, **params) -> dict | list:
        resp = self._client.get(path, params=params or None)
        resp.raise_for_status()
        return resp.json()

    def _items(self, path: str, **params) -> list[dict]:
        data = self._get(path, **params)
        if isinstance(data, dict):
            return data.get("items", [])
        return data if isinstance(data, list) else []

    def get_account(self) -> dict:
        return self._get("/account/me")

    def get_children(self) -> list[dict]:
        return self._items("/child")

    def get_groups(self, scope: str | None = None) -> list[dict]:
        params = {"dtype": "identity.RHomeGroup"}
        if scope:
            params["scope"] = scope
        return self._items("/group", **params)

    def get_announcements(self, group_id: int | None = None) -> list[dict]:
        params: dict = {"dtype": "event.RAnnouncementEvent"}
        if group_id:
            params["group"] = group_id
        return self._items("/event", **params)

    def get_chatrooms(self) -> list[dict]:
        return self._items("/chatroom")

    def get_chat_messages(self, chatroom_id: int) -> list[dict]:
        return self._items(f"/chatroom/{chatroom_id}/chatmessage")

    def get_calendar_urls(self) -> list[str]:
        data = self._get("/calendar/sync")
        return data.get("strings", [])

    def get_unread_counts(self) -> list[dict]:
        return self._items("/identity/unreadcounts")

    def get_all_announcements(self, limit: int | None = None) -> list[dict]:
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
            items = self.get_announcements(group_id=gid)
            for item in items:
                item["_group_name"] = gname
            all_items.extend(items)

        all_items.sort(key=lambda a: a.get("sortDate", ""))
        if limit is not None:
            all_items = all_items[-limit:]
        return all_items

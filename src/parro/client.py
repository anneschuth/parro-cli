"""Parro API client - real implementation using rest-v2.parro.com.

Authentication uses OAuth2 authorization code flow with PKCE via
inloggen.parnassys.net. Tokens are stored locally and refreshed
automatically.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import threading
import webbrowser
from datetime import datetime
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
LOCAL_CALLBACK = "http://localhost:18923/callback"

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
    def login() -> dict:
        """Run the OAuth2 authorization code flow with PKCE.

        Opens a browser for the user to log in. After login, the IDP
        redirects to parro://oauth2?code=..., which doesn't work on
        desktop. We serve a local page that captures the code via JS
        before the redirect completes.

        Returns the token response dict.
        """
        verifier, challenge = _generate_pkce()
        state = secrets.token_urlsafe(32)

        import urllib.parse

        auth_params = urllib.parse.urlencode(
            {
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": "openid",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        auth_url = f"{AUTHORIZE_URL}?{auth_params}"

        result: dict = {}

        # HTML page that opens the OAuth flow in an iframe from the
        # IDP domain, then the user logs in. After login the IDP
        # redirects to parro://oauth2?code=... We can't intercept
        # that in the browser, so we ask the user to paste the URL.
        # But better: we serve a page that does the flow and captures
        # the code via a popup that we control.
        login_page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Parro Login</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif;
         max-width: 600px; margin: 60px auto; padding: 20px;
         background: #fdf2f8; color: #1a1a1a; }}
  h1 {{ color: #e8436e; }}
  .url-input {{ width: 100%; padding: 12px; font-size: 14px;
                border: 2px solid #e8436e; border-radius: 8px;
                margin: 10px 0; }}
  button {{ background: #e8436e; color: white; border: none;
            padding: 12px 24px; border-radius: 8px; cursor: pointer;
            font-size: 16px; }}
  button:hover {{ background: #d63361; }}
  .step {{ margin: 20px 0; padding: 15px; background: white;
           border-radius: 8px; border-left: 4px solid #e8436e; }}
  .success {{ background: #dcfce7; border-left-color: #22c55e; }}
  #status {{ margin-top: 20px; }}
</style></head><body>
<h1>Parro Login</h1>
<div class="step">
  <strong>Stap 1:</strong> Klik om in te loggen bij Parro
  <br><br>
  <a href="{auth_url}" target="_blank">
    <button>Inloggen bij Parro</button>
  </a>
</div>
<div class="step">
  <strong>Stap 2:</strong> Na het inloggen probeert de browser
  <code>parro://oauth2?code=...</code> te openen. Dit lukt niet.
  <br><br>
  Kopieer de <strong>volledige URL</strong> uit de adresbalk
  (begint met <code>parro://oauth2</code>) en plak hier:
  <br><br>
  <input type="text" id="url" class="url-input"
         placeholder="parro://oauth2?code=...&state=...">
  <br>
  <button onclick="submitCode()">Verstuur</button>
</div>
<div id="status"></div>
<script>
function submitCode() {{
  const url = document.getElementById('url').value;
  const params = new URLSearchParams(url.split('?')[1] || '');
  const code = params.get('code');
  if (!code) {{
    document.getElementById('status').innerHTML =
      '<div class="step" style="border-left-color:red">Geen code gevonden in de URL</div>';
    return;
  }}
  fetch('/callback?code=' + encodeURIComponent(code) + '&state=' + encodeURIComponent(params.get('state') || ''))
    .then(r => r.text())
    .then(t => {{
      document.getElementById('status').innerHTML =
        '<div class="step success"><strong>Gelukt!</strong> Je bent ingelogd. Dit venster mag dicht.</div>';
    }})
    .catch(e => {{
      document.getElementById('status').innerHTML =
        '<div class="step" style="border-left-color:red">Fout: ' + e + '</div>';
    }});
}}
// Auto-detect if opened via parro:// redirect (won't work but try)
window.addEventListener('hashchange', function() {{
  const hash = window.location.hash;
  if (hash.includes('code=')) submitCode();
}});
</script></body></html>"""

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)

                if parsed.path == "/callback":
                    qs = urllib.parse.parse_qs(parsed.query)
                    if "code" in qs:
                        result["code"] = qs["code"][0]
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(b"OK")
                        threading.Thread(
                            target=self.server.shutdown, daemon=True
                        ).start()
                        return

                # Serve the login page
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(login_page.encode())

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("localhost", 18923), Handler)
        webbrowser.open("http://localhost:18923")
        server.serve_forever()

        if "code" not in result:
            raise RuntimeError("Login geannuleerd of mislukt.")

        # Exchange code for tokens
        token_resp = httpx.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": result["code"],
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
            timeout=30,
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        if "access_token" not in tokens:
            raise RuntimeError(f"Token exchange mislukt: {tokens}")

        _save_tokens(tokens)
        return tokens

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

        # Try the access token first
        access_token = tokens.get("access_token", "")
        if access_token:
            # Quick validation: try /account/me
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

        # Try refresh
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
            raise RuntimeError(
                "Not authenticated. Run `parro login` first."
            )
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

    def get_absence_setting(self) -> dict:
        return self._get("/absence/setting")

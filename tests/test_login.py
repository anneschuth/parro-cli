"""Tests for the headless login flow (form field detection + account chooser)."""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from parro.client import (
    IDP_BASE,
    ParroAuth,
    _login_field_names,
    _parse_account_chooser,
)

LOGIN_PAGE = """
<form class="sign-in__form" method="post" id="loginForm"
      action="./?-1.-signIn-mainPanel-signInFormPanel-signInForm&amp;auth=TOKEN">
  <input type="text" maxlength="80" autocomplete="username" value="" name="emailadres"
         id="signin-email"/>
  <input type="password" maxlength="172" autocomplete="current-password" value=""
         name="wachtwoord" id="signin-password"/>
  <button type="button" class="form-field__toggle" aria-controls="signin-password"></button>
</form>
"""

OLD_LOGIN_PAGE = """
<form action="./?-1.-signIn-form">
  <input type="hidden" name="csrf" value="abc"/>
  <input type="text" name="e-mailadres"/>
  <input type="password" name="wachtwoord"/>
</form>
"""

ACCOUNT_CHOOSER = """
<html><head><script>
Wicket.Ajax.baseUrl="wicket/page?1";
Wicket.Ajax.ajax({"u":"./page?1-1.0-signIn-accountKeuze-accounts-account-0","c":"id1",
  "e":"click keydown"});
Wicket.Ajax.ajax({"u":"./page?1-1.0-signIn-accountKeuze-accounts-account-1","c":"id2",
  "e":"click keydown"});
</script></head><body>
<h1 class="sign-in__title-left">Account kiezen</h1>
<ul class="account-list" id="id3">
  <li class="account-list__item" id="id1">
    <a class="account-list__link" role="button">
      <span class="account-list__text">
        <span class="account-list__name"><span></span><span>Jan Jansen</span></span>
        <span class="account-list__role"><span>Verzorger</span> bij
          <span>De Regenboog</span></span>
      </span>
    </a>
  </li>
  <li class="account-list__item" id="id2">
    <a class="account-list__link" role="button">
      <span class="account-list__text">
        <span class="account-list__name"><span></span><span>Piet Pietersen</span></span>
        <span class="account-list__role"><span>Verzorger</span> bij
          <span>De Regenboog</span></span>
      </span>
    </a>
  </li>
</ul>
<a href="./page?1-1.-signIn-annuleren">Annuleren</a>
</body></html>
"""


class TestLoginFieldNames:
    def test_current_form(self):
        assert _login_field_names(LOGIN_PAGE) == ("emailadres", "wachtwoord")

    def test_old_form_with_dash(self):
        assert _login_field_names(OLD_LOGIN_PAGE) == ("e-mailadres", "wachtwoord")

    def test_unparseable_falls_back_to_known_names(self):
        assert _login_field_names("<html></html>") == ("emailadres", "wachtwoord")


class TestParseAccountChooser:
    def test_parses_all_entries_in_order(self):
        accounts = _parse_account_chooser(ACCOUNT_CHOOSER)
        assert [a["name"] for a in accounts] == ["Jan Jansen", "Piet Pietersen"]
        assert accounts[0]["role"] == "Verzorger bij De Regenboog"
        assert accounts[0]["url"].endswith("accounts-account-0")
        assert accounts[0]["focus_id"] == "id1"
        assert accounts[1]["url"].endswith("accounts-account-1")
        assert accounts[1]["focus_id"] == "id2"

    def test_not_a_chooser(self):
        assert _parse_account_chooser(LOGIN_PAGE) == []


def _make_transport(state: dict, with_chooser: bool = True) -> httpx.MockTransport:
    """Simulate the ParnaSys IDP: authorize → login form → (chooser) → parro:// code → token."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        path = request.url.path
        if path == "/idp/oauth2/authorize":
            return httpx.Response(302, headers={"location": "/idp/?auth=TOKEN"})
        if path == "/idp/" and request.method == "GET":
            return httpx.Response(200, text=LOGIN_PAGE)
        if path == "/idp/" and request.method == "POST":
            state["posted"] = dict(httpx.QueryParams(request.content.decode()))
            if with_chooser:
                return httpx.Response(302, headers={"location": f"{IDP_BASE}/idp/wicket/page?1"})
            return httpx.Response(302, headers={"location": "parro://oauth2?code=CODE&state=x"})
        if url == f"{IDP_BASE}/idp/wicket/page?1":
            return httpx.Response(200, text=ACCOUNT_CHOOSER)
        if "accountKeuze-accounts-account-" in url:
            state["ajax_url"] = url
            state["ajax_headers"] = dict(request.headers)
            return httpx.Response(
                200,
                headers={"ajax-location": "parro://oauth2:443/?code=CODE&state=x"},
                text="<ajax-response><redirect><![CDATA[parro://oauth2:443/?code=CODE"
                "&state=x]]></redirect></ajax-response>",
            )
        if path == "/idp/oauth2/token":
            state["token_form"] = dict(httpx.QueryParams(request.content.decode()))
            return httpx.Response(
                200, json={"access_token": "AT", "refresh_token": "RT", "expires_in": 3599}
            )
        return httpx.Response(404, text=f"unexpected {request.method} {url}")

    return httpx.MockTransport(handler)


def _run_login(state: dict, with_chooser: bool = True, **kwargs) -> dict[str, str]:
    transport = _make_transport(state, with_chooser)
    real_client = httpx.Client

    def fake_client(**kw):
        return real_client(transport=transport, **kw)

    with (
        patch("parro.client.httpx.Client", side_effect=fake_client),
        patch("parro.client._save_tokens") as save,
    ):
        tokens = ParroAuth.login(username="jan@example.nl", password="geheim", **kwargs)
    state["saved"] = save.call_args.args[0] if save.call_args else None
    return tokens


class TestLoginFlow:
    def test_posts_credentials_with_form_field_names(self):
        state: dict = {}
        _run_login(state, with_chooser=False)
        assert state["posted"]["emailadres"] == "jan@example.nl"
        assert state["posted"]["wachtwoord"] == "geheim"
        assert "e-mailadres" not in state["posted"]

    def test_without_account_chooser(self):
        state: dict = {}
        tokens = _run_login(state, with_chooser=False)
        assert tokens["access_token"] == "AT"
        assert state["token_form"]["code"] == "CODE"
        assert state["saved"] == tokens

    def test_account_chooser_defaults_to_first(self):
        state: dict = {}
        tokens = _run_login(state)
        assert tokens["access_token"] == "AT"
        assert state["ajax_url"].endswith("accounts-account-0")
        assert state["ajax_headers"]["wicket-ajax"] == "true"
        assert state["ajax_headers"]["wicket-ajax-baseurl"] == "wicket/page?1"
        assert state["ajax_headers"]["wicket-focusedelementid"] == "id1"
        assert state["token_form"]["code"] == "CODE"

    def test_account_chooser_picks_named_account(self):
        state: dict = {}
        _run_login(state, account="piet")
        assert state["ajax_url"].endswith("accounts-account-1")
        assert state["ajax_headers"]["wicket-focusedelementid"] == "id2"

    def test_account_chooser_unknown_account_lists_options(self):
        state: dict = {}
        with pytest.raises(RuntimeError, match="Jan Jansen.*Piet Pietersen"):
            _run_login(state, account="klaas")

    def test_saved_tokens_are_json_serialisable(self):
        state: dict = {}
        _run_login(state)
        json.dumps(state["saved"])

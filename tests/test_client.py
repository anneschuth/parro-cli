"""Tests for parro.client."""

from __future__ import annotations

import json
import base64
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from parro.client import _generate_pkce, _save_tokens, _load_tokens, ParroClient


class TestGeneratePkce:
    def test_returns_tuple_of_two_strings(self):
        verifier, challenge = _generate_pkce()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)

    def test_verifier_length(self):
        verifier, _ = _generate_pkce()
        # PKCE spec: 43-128 characters
        assert 43 <= len(verifier) <= 128

    def test_challenge_is_valid_base64url(self):
        verifier, challenge = _generate_pkce()
        # Should not contain padding or non-url-safe chars
        assert "=" not in challenge
        assert "+" not in challenge
        assert "/" not in challenge

    def test_challenge_matches_verifier(self):
        verifier, challenge = _generate_pkce()
        # Recompute the challenge from the verifier
        digest = hashlib.sha256(verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert challenge == expected

    def test_unique_each_call(self):
        v1, c1 = _generate_pkce()
        v2, c2 = _generate_pkce()
        assert v1 != v2
        assert c1 != c2


class TestSaveLoadTokens:
    def test_round_trip(self, tmp_path):
        token_file = tmp_path / "tokens.json"
        tokens = {"access_token": "abc123", "refresh_token": "def456"}

        with patch("parro.client.TOKEN_PATH", token_file):
            _save_tokens(tokens)
            loaded = _load_tokens()

        assert loaded == tokens

    def test_load_nonexistent_returns_none(self, tmp_path):
        token_file = tmp_path / "nonexistent" / "tokens.json"
        with patch("parro.client.TOKEN_PATH", token_file):
            assert _load_tokens() is None

    def test_load_invalid_json_returns_none(self, tmp_path):
        token_file = tmp_path / "tokens.json"
        token_file.write_text("not valid json {{{")
        with patch("parro.client.TOKEN_PATH", token_file):
            assert _load_tokens() is None

    def test_save_creates_parent_dirs(self, tmp_path):
        token_file = tmp_path / "deep" / "nested" / "tokens.json"
        tokens = {"access_token": "test"}

        with patch("parro.client.TOKEN_PATH", token_file):
            _save_tokens(tokens)

        assert token_file.exists()
        assert json.loads(token_file.read_text()) == tokens

    def test_file_permissions(self, tmp_path):
        token_file = tmp_path / "tokens.json"
        tokens = {"access_token": "secret"}

        with patch("parro.client.TOKEN_PATH", token_file):
            _save_tokens(tokens)

        # File should be readable only by owner (0o600)
        import stat
        mode = token_file.stat().st_mode & 0o777
        assert mode == 0o600


class TestParroClientNotAuthenticated:
    def test_raises_when_no_token(self):
        """ParroClient should raise RuntimeError when used without auth."""
        with patch("parro.client.ParroAuth.get_token", return_value=None):
            with pytest.raises(RuntimeError, match="Not authenticated"):
                with ParroClient() as client:
                    pass

    def test_raises_with_message_about_login(self):
        """Error message should tell the user to run parro login."""
        with patch("parro.client.ParroAuth.get_token", return_value=None):
            with pytest.raises(RuntimeError, match="parro login"):
                with ParroClient() as client:
                    pass

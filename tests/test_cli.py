"""Tests for parro.cli using Click's CliRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from parro.cli import _fmt_date, cli

runner = CliRunner()


# --- Helper function tests ---


class TestFmtDate:
    def test_valid_iso(self):
        result = _fmt_date("2024-03-15T14:30:00")
        assert "15" in result
        assert "14:30" in result

    def test_empty_string(self):
        assert _fmt_date("") == ""

    def test_none_input(self):
        assert _fmt_date(None) == ""

    def test_invalid_iso_falls_back(self):
        result = _fmt_date("not-a-date-but-long-enough")
        assert result == "not-a-date-but-l"


# --- CLI command tests ---


class TestMainHelp:
    def test_help_shows_all_commands(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        expected_commands = [
            "login",
            "logout",
            "account",
            "announcements",
            "chatrooms",
            "messages",
            "open",
            "children",
            "groups",
            "unread",
            "calendar",
            "completion",
        ]
        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not found in help output"

    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        import re

        assert re.search(r"\d+\.\d+\.\d+", result.output)


class TestLoginCommand:
    def test_help(self):
        result = runner.invoke(cli, ["login", "--help"])
        assert result.exit_code == 0
        assert "--username" in result.output or "-u" in result.output
        assert "--password" in result.output or "-p" in result.output
        assert "--store" in result.output

    def test_store_saves_env_file(self, tmp_path):
        """--store should write credentials to ~/.config/parro/.env."""
        env_file = tmp_path / ".env"
        fake_tokens = {"access_token": "tok123"}
        fake_account = {"email": "test@example.com"}

        with (
            patch("parro.cli.ParroAuth.login", return_value=fake_tokens),
            patch("parro.cli.ParroClient") as mock_client_cls,
            patch("parro.client.TOKEN_PATH", tmp_path / "tokens.json"),
        ):
            ctx = mock_client_cls.return_value.__enter__.return_value
            ctx.get_account.return_value = fake_account
            # Patch TOKEN_PATH.parent / ".env" to point to our tmp_path
            with patch("parro.cli.Path", wraps=Path) as _:
                # Simpler: just patch the env_path directly via TOKEN_PATH
                from parro import client as client_mod

                original = client_mod.TOKEN_PATH
                client_mod.TOKEN_PATH = tmp_path / "tokens.json"
                try:
                    result = runner.invoke(
                        cli,
                        [
                            "login",
                            "-u",
                            "user@test.nl",
                            "-p",
                            "secret",
                            "--store",
                        ],
                    )
                finally:
                    client_mod.TOKEN_PATH = original

            assert result.exit_code == 0
            assert env_file.exists()
            content = env_file.read_text()
            assert "PARRO_USERNAME=user@test.nl" in content
            assert "PARRO_PASSWORD=secret" in content
            # File should be owner-only readable
            mode = env_file.stat().st_mode & 0o777
            assert mode == 0o600


class TestLogoutCommand:
    def test_help(self):
        result = runner.invoke(cli, ["logout", "--help"])
        assert result.exit_code == 0

    def test_not_logged_in(self):
        """Logout when no tokens file exists should print a message."""
        with patch("parro.cli.Path.exists", return_value=False):
            # We need to patch at the module level where TOKEN_PATH is used
            import os
            import tempfile

            from parro.client import TOKEN_PATH

            # Use a fake token path that doesn't exist
            fake_path = os.path.join(tempfile.gettempdir(), "parro-test-nonexistent-tokens.json")
            with patch("parro.client.TOKEN_PATH", new=type(TOKEN_PATH)(fake_path)):
                result = runner.invoke(cli, ["logout"])
                assert result.exit_code == 0
                assert "uitgelogd" in result.output.lower()


class TestAccountCommand:
    def test_help(self):
        result = runner.invoke(cli, ["account", "--help"])
        assert result.exit_code == 0


class TestAnnouncementsCommand:
    def test_help(self):
        result = runner.invoke(cli, ["announcements", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output
        assert "--group" in result.output


class TestChatroomsCommand:
    def test_help(self):
        result = runner.invoke(cli, ["chatrooms", "--help"])
        assert result.exit_code == 0


class TestMessagesCommand:
    def test_help(self):
        result = runner.invoke(cli, ["messages", "--help"])
        assert result.exit_code == 0
        assert "CHATROOM_ID" in result.output


class TestOpenCommand:
    def test_help(self):
        result = runner.invoke(cli, ["open", "--help"])
        assert result.exit_code == 0
        assert "REF" in result.output

    def test_invalid_number_no_cache(self):
        """Opening a non-existent attachment number should fail."""
        with patch("parro.cli._load_attachment_urls", return_value=[]):
            result = runner.invoke(cli, ["open", "999"])
            assert result.exit_code != 0

    def test_invalid_number_out_of_range(self):
        """Opening an out-of-range number should fail."""
        with patch("parro.cli._load_attachment_urls", return_value=["http://example.com/a.pdf"]):
            result = runner.invoke(cli, ["open", "5"])
            assert result.exit_code != 0


class TestChildrenCommand:
    def test_help(self):
        result = runner.invoke(cli, ["children", "--help"])
        assert result.exit_code == 0


class TestGroupsCommand:
    def test_help(self):
        result = runner.invoke(cli, ["groups", "--help"])
        assert result.exit_code == 0


class TestUnreadCommand:
    def test_help(self):
        result = runner.invoke(cli, ["unread", "--help"])
        assert result.exit_code == 0


class TestCalendarCommand:
    def test_help(self):
        result = runner.invoke(cli, ["calendar", "--help"])
        assert result.exit_code == 0


class TestCompletionCommand:
    def test_help(self):
        result = runner.invoke(cli, ["completion", "--help"])
        assert result.exit_code == 0
        assert "bash" in result.output.lower()
        assert "zsh" in result.output.lower()
        assert "fish" in result.output.lower()

    def test_invalid_shell(self):
        result = runner.invoke(cli, ["completion", "powershell"])
        assert result.exit_code != 0

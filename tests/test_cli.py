"""Tests for parro.cli using Click's CliRunner."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from parro.cli import cli, _fmt_date, _identity_name, _link_id


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


class TestIdentityName:
    def test_display_name(self):
        assert _identity_name({"displayName": "Jan Jansen"}) == "Jan Jansen"

    def test_first_last(self):
        assert _identity_name({"firstName": "Jan", "surname": "Jansen"}) == "Jan Jansen"

    def test_first_prefix_last(self):
        result = _identity_name({
            "firstName": "Jan",
            "surnamePrefix": "van",
            "surname": "Dijk",
        })
        assert result == "Jan van Dijk"

    def test_empty_returns_onbekend(self):
        assert _identity_name({}) == "Onbekend"

    def test_display_name_takes_priority(self):
        result = _identity_name({
            "displayName": "Display",
            "firstName": "First",
            "surname": "Last",
        })
        assert result == "Display"


class TestLinkId:
    def test_self_link(self):
        item = {"links": [{"rel": "self", "id": 42}]}
        assert _link_id(item) == 42

    def test_custom_rel(self):
        item = {"links": [{"rel": "parent", "id": 99}]}
        assert _link_id(item, rel="parent") == 99

    def test_no_links(self):
        assert _link_id({}) is None

    def test_no_matching_rel(self):
        item = {"links": [{"rel": "other", "id": 1}]}
        assert _link_id(item) is None


# --- CLI command tests ---


class TestMainHelp:
    def test_help_shows_all_commands(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        expected_commands = [
            "login", "logout", "account", "announcements",
            "chatrooms", "messages", "open", "children",
            "groups", "unread", "calendar", "completion",
        ]
        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not found in help output"

    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output


class TestLoginCommand:
    def test_help(self):
        result = runner.invoke(cli, ["login", "--help"])
        assert result.exit_code == 0
        assert "--username" in result.output or "-u" in result.output
        assert "--password" in result.output or "-p" in result.output


class TestLogoutCommand:
    def test_help(self):
        result = runner.invoke(cli, ["logout", "--help"])
        assert result.exit_code == 0

    def test_not_logged_in(self):
        """Logout when no tokens file exists should print a message."""
        with patch("parro.cli.Path.exists", return_value=False):
            # We need to patch at the module level where TOKEN_PATH is used
            from parro.client import TOKEN_PATH
            import tempfile
            import os

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

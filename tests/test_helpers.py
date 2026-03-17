"""Tests for parro.helpers."""

from __future__ import annotations

from parro.helpers import identity_name, link_id


class TestIdentityName:
    def test_display_name(self):
        assert identity_name({"displayName": "Jan Jansen"}) == "Jan Jansen"

    def test_first_last(self):
        assert identity_name({"firstName": "Jan", "surname": "Jansen"}) == "Jan Jansen"

    def test_first_prefix_last(self):
        result = identity_name(
            {
                "firstName": "Jan",
                "surnamePrefix": "van",
                "surname": "Dijk",
            }
        )
        assert result == "Jan van Dijk"

    def test_empty_returns_onbekend(self):
        assert identity_name({}) == "Onbekend"

    def test_display_name_takes_priority(self):
        result = identity_name(
            {
                "displayName": "Display",
                "firstName": "First",
                "surname": "Last",
            }
        )
        assert result == "Display"


class TestLinkId:
    def test_self_link(self):
        item = {"links": [{"rel": "self", "id": 42}]}
        assert link_id(item) == 42

    def test_custom_rel(self):
        item = {"links": [{"rel": "parent", "id": 99}]}
        assert link_id(item, rel="parent") == 99

    def test_no_links(self):
        assert link_id({}) is None

    def test_no_matching_rel(self):
        item = {"links": [{"rel": "other", "id": 1}]}
        assert link_id(item) is None

"""Reusable helpers for Parro data structures.

Pure stdlib — no external dependencies.
"""

from __future__ import annotations


def link_id(item: dict, rel: str = "self") -> int | None:
    """Extract the ID from a HAL-style link with the given relation."""
    for link in item.get("links", []):
        if link.get("rel") == rel:
            return link.get("id")
    return None


def identity_name(identity: dict) -> str:
    """Extract display name from an identity object.

    Falls back to firstName + surnamePrefix + surname when displayName
    is absent.  Returns "Onbekend" if nothing is available.
    """
    name = identity.get("displayName", "")
    if not name:
        first = identity.get("firstName", "")
        prefix = identity.get("surnamePrefix", "")
        last = identity.get("surname", "")
        parts = [first, prefix, last] if prefix else [first, last]
        name = " ".join(p for p in parts if p)
    return name or "Onbekend"

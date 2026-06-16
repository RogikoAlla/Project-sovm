"""Parsing of raw player input for the King and Servant client."""

from __future__ import annotations

from common.constants import SUITS
from common.i18n import get_translator

_ = get_translator()


def parse_card_indices(raw: str, hand_size: int) -> tuple[list[int] | None, str]:
    """Parse a space-separated list of card indices into ``(indices, error)``."""
    tokens = raw.split()
    if not tokens:
        return None, _("No cards selected.")

    indices: list[int] = []
    for token in tokens:
        if not token.lstrip("-").isdigit():
            return None, _("'{token}' is not a number.").format(token=token)
        value = int(token)
        if value < 0 or value >= hand_size:
            return None, _("Index {value} is out of range.").format(value=value)
        if value in indices:
            return None, _("Index {value} is repeated.").format(value=value)
        indices.append(value)

    return indices, ""


def parse_suit(raw: str) -> tuple[str | None, str]:
    """Parse a trump suit (name or index) into ``(suit, error)``."""
    token = raw.strip().lower()
    if not token:
        return None, _("No suit selected.")

    if token.isdigit():
        index = int(token)
        if 0 <= index < len(SUITS):
            return SUITS[index], ""
        return None, _("Suit number {index} is out of range.").format(index=index)

    if token in SUITS:
        return token, ""

    return None, _("'{token}' is not a valid suit.").format(token=token)

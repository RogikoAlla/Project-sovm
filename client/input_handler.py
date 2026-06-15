"""Parsing of raw player input for the King and Servant client.

Pure functions that turn the text a player types into structured values.
They never read from stdin or touch the network, so they are easy to test.
"""

from __future__ import annotations

from common.i18n import get_translator

_ = get_translator()


def parse_card_indices(raw: str, hand_size: int) -> tuple[list[int] | None, str]:
    """Parse a space-separated list of card indices.

    Args:
        raw: Text typed by the player, e.g. ``"0 2 3"``.
        hand_size: Number of cards currently in the player's hand.

    Returns:
        ``(indices, "")`` on success, or ``(None, error_message)`` if the
        input is empty, non-numeric, out of range, or has duplicates.
    """
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

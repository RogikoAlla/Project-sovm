"""Terminal rendering for the King and Servant client.

Pure formatting helpers: each function turns game data into a string,
so they are easy to test and free of any I/O or networking.
"""

from __future__ import annotations

from common.constants import SUIT_SYMBOLS
from common.i18n import get_translator
from common.models import Card

_ = get_translator()


def render_card(card: Card) -> str:
    """Return a short label for a card, e.g. ``'K♠'``."""
    return f"{card.rank}{SUIT_SYMBOLS.get(card.suit, card.suit)}"


def render_hand(hand: list[Card]) -> str:
    """Return the player's hand as a numbered, space-separated row."""
    if not hand:
        return _("Your hand is empty.")
    cells = [f"[{i}] {render_card(c)}" for i, c in enumerate(hand)]
    return "  ".join(cells)

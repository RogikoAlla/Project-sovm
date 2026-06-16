"""Terminal rendering helpers for the King and Servant client."""

from __future__ import annotations

from common.constants import SUIT_SYMBOLS
from common.i18n import get_translator
from common.models import Card, GameState

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


def render_table(state: GameState) -> str:
    """Return the cards on the table as attack/defense pairs."""
    if not state.table_attack:
        return _("Table is empty.")
    rows = []
    for idx, atk in enumerate(state.table_attack):
        defense = state.table_defense.get(idx) or state.table_defense.get(str(idx))
        if defense is not None:
            rows.append(f"{render_card(atk)} -> {render_card(defense)}")
        else:
            rows.append(f"{render_card(atk)} -> ?")
    return "  |  ".join(rows)


def render_players(state: GameState) -> str:
    """Return one line per player with role, hand size and turn markers."""
    lines = []
    for p in state.players:
        marker = " "
        if p.player_id == state.current_attacker_id:
            marker = "A"
        elif p.player_id == state.current_defender_id:
            marker = "D"
        role = p.role or "-"
        lines.append(f"{marker} {p.name} ({role}) — {p.hand_size}")
    return "\n".join(lines)


def render_state(state: GameState) -> str:
    """Return a full text snapshot of the current game state."""
    trump = SUIT_SYMBOLS.get(state.trump_suit, state.trump_suit)
    header = _("Round {n} | Trump: {trump}").format(n=state.round_number, trump=trump)
    parts = [
        header,
        render_players(state),
        _("Table:") + " " + render_table(state),
        _("Hand:") + " " + render_hand(state.your_hand),
    ]
    if state.message:
        parts.append(state.message)
    return "\n".join(parts)

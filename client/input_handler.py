"""Pure input parsing and menu-formatting helpers (no blocking socket I/O)."""

from __future__ import annotations

import builtins
from typing import Optional, Union

from common.constants import SUIT_SYMBOLS
from common.i18n import setup_i18n
from common.models import Card

# Ensure _() is available even if main has not called setup_i18n yet.
if not hasattr(builtins, "_"):
    setup_i18n()


def prompt_name() -> str:
    """Prompt for the player's display name until non-empty."""
    while True:
        name = input(_("Enter your name: ")).strip()
        if name:
            return name
        print(_("Name cannot be empty."))


def suits_in_hand(hand: list[Card]) -> list[str]:
    """Return suits present in *hand* in canonical display order."""
    order = ["spades", "hearts", "diamonds", "clubs"]
    return [s for s in order if any(c.suit == s for c in hand)]


def format_trump_menu(suits: list[str], hand: list[Card]) -> str:
    """Build the trump-selection menu string."""
    lines = [
        "",
        f"  === {_('Choose trump suit')} ===",
        f"  {_('Suits in your hand:')}",
    ]
    for i, suit in enumerate(suits, 1):
        sym = SUIT_SYMBOLS.get(suit, suit)
        count = sum(1 for c in hand if c.suit == suit)
        lines.append(f"    [{i}] {sym} {_(suit)}  ({count})")
    lines.append(f"  {_('Enter suit number:')}")
    return "\n".join(lines)


def parse_trump_choice(line: str, suits: list[str]) -> Optional[str]:
    """Parse a trump-menu selection into a suit name, or None if invalid."""
    try:
        idx = int(line.strip()) - 1
    except ValueError:
        return None
    if 0 <= idx < len(suits):
        return suits[idx]
    return None


def most_common_suit(hand: list[Card]) -> str:
    """Return the suit with the most cards in *hand* (fallback trump)."""
    counts: dict[str, int] = {}
    for card in hand:
        counts[card.suit] = counts.get(card.suit, 0) + 1
    return max(counts, key=lambda s: counts[s]) if counts else "spades"


def format_swap_menu(others: list[dict]) -> str:
    """Build the blind-swap target menu with 1-based numbers."""
    lines = ["", f"  === {_('Blind swap')} ==="]
    for i, p in enumerate(others, 1):
        role = _(p["role"]) if p.get("role") else "?"
        lines.append(f"    [{i}] {p['name']}  ({role})")
    lines.append("    [0] -")
    return "\n".join(lines)


def parse_swap_choice(line: str, others: list[dict]) -> Union[int, str, None]:
    """Parse a swap selection: target id, 'skip' for 0, or None if invalid."""
    line = line.strip()
    if line == "0":
        return "skip"
    try:
        idx = int(line) - 1
    except ValueError:
        return None
    if 0 <= idx < len(others):
        return int(others[idx]["id"])
    return None


def format_attack_hint() -> str:
    """Build the attack prompt hint string."""
    return f"\n  === {_('Your attack turn')} ===\n  1 3 5 | 0"


def parse_attack(line: str, hand: list[Card]) -> Union[list[Card], str, None]:
    """Parse an attack: list of cards, 'pass' for 0, or None if invalid."""
    line = line.strip()
    if line == "0":
        return "pass"
    try:
        idx = [int(x) - 1 for x in line.split()]
    except ValueError:
        return None
    if not idx or len(set(idx)) != len(idx):
        return None
    if not all(0 <= i < len(hand) for i in idx):
        return None
    return [hand[i] for i in idx]


def format_defense_hint() -> str:
    """Build the defense prompt hint string."""
    return f"\n  === {_('Your defense turn')} ===\n  1-3 2-5 | 0"


def parse_defense(
    line: str,
    hand: list[Card],
    table_attack: list[Card],
    table_defense: dict,
) -> Union[list[tuple[int, Card]], str, None]:
    """Parse defense pairs 'slot-handcard', 'take' for 0, or None if invalid."""
    line = line.strip()
    if line == "0":
        return "take"

    pairs: list[tuple[int, Card]] = []
    used_hand: set[int] = set()
    used_slot: set[int] = set()

    for token in line.split():
        parts = token.split("-")
        if len(parts) != 2:
            return None
        try:
            slot = int(parts[0]) - 1
            hand_i = int(parts[1]) - 1
        except ValueError:
            return None
        if not (0 <= slot < len(table_attack)):
            return None
        if str(slot) in table_defense:
            return None
        if not (0 <= hand_i < len(hand)):
            return None
        if slot in used_slot or hand_i in used_hand:
            return None
        used_slot.add(slot)
        used_hand.add(hand_i)
        pairs.append((slot, hand[hand_i]))

    return pairs if pairs else None

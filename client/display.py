"""Console display helpers: render the game state to the terminal."""

from __future__ import annotations

import os
import sys
import builtins

from common.constants import SUIT_SYMBOLS
from common.i18n import setup_i18n, translate_message
from common.models import Card, GameState

if not hasattr(builtins, "_"):
    setup_i18n()

_RESET = "\033[0m"
_RED = "\033[91m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_YELLOW = "\033[93m"


def _(text: str) -> str:
    """Translate using the currently installed locale."""
    return builtins._(text)


def clear_screen() -> None:
    """Clear the terminal screen portably."""
    os.system("cls" if os.name == "nt" else "clear")


def card_str(card: Card) -> str:
    """Return a coloured ANSI string for a card."""
    label = str(card)
    if card.suit in ("hearts", "diamonds"):
        return f"{_RED}{_BOLD}{label}{_RESET}"
    return f"{_BOLD}{label}{_RESET}"


def render_hand_numbered(hand: list[Card]) -> str:
    """Render a hand as a numbered list, one card per line."""
    if not hand:
        return f"    {_('-')}"
    return "\n".join(f"    [{i:2}] {card_str(c)}" for i, c in enumerate(hand, 1))


def render_table(attack_cards: list[Card], defense_cards: dict, trump_suit: str) -> str:
    """Render the table with 1-based attack slots and their defenders."""
    trump_sym = SUIT_SYMBOLS.get(trump_suit, "?")
    trump_label = _(trump_suit) if trump_suit else _("not declared")

    lines = [
        f"  {_('Trump:')} {_BOLD}{trump_sym} {trump_label}{_RESET}",
        f"  {_('Table:')}"
    ]

    if not attack_cards:
        lines.append(f"    {_('-')}")
        return "\n".join(lines)

    for i, atk in enumerate(attack_cards):
        dfn = defense_cards.get(str(i)) or defense_cards.get(i)

        if dfn:
            lines.append(
                f"    [{i + 1}] {card_str(atk)}  ->  {card_str(dfn)}"
            )
        else:
            lines.append(
                f"    [{i + 1}] {card_str(atk)}  {_YELLOW}<- {_('open')}{_RESET}"
            )

    return "\n".join(lines)


def render_players(state: GameState, my_id: int) -> str:
    """Render the player roster with roles, hand sizes and turn markers."""
    lines = [f"  {_('Players:')}"]

    for p in state.players:
        you = f" {_YELLOW}<- {_('YOU')}{_RESET}" if p.player_id == my_id else ""
        out = "" if p.is_active else f" {_DIM}{_('[out]')}{_RESET}"
        role = _(p.role) if p.role else "?"

        lines.append(
            f"    {p.name:15} | {role:8} | {p.hand_size}{out}{you}"
        )

    return "\n".join(lines)


def render_state(state: GameState, my_id: int) -> None:
    """Clear the screen and print the full game state."""
    clear_screen()

    print("=" * 60)
    print(
        f"  {_BOLD}{_('KING AND SERVANT')}{_RESET}   "
        f"{_('Round')} {state.round_number}"
    )
    print("=" * 60)

    print(render_players(state, my_id))
    print()

    print(render_table(state.table_attack, state.table_defense, state.trump_suit))
    print()

    print(f"  {_('Your hand')}:")
    print(render_hand_numbered(state.your_hand))

    if state.message:
        print(f"\n  {_YELLOW}>> {translate_message(state.message)}{_RESET}")

    print("=" * 60)


def print_timer(label: str, seconds_left: int, total: int = 60) -> None:
    """Print an in-place countdown bar using a carriage return."""
    bar_len = 20
    filled = int(bar_len * seconds_left / total) if total else 0
    bar = "#" * filled + "." * (bar_len - filled)

    colour = _RED if seconds_left <= 5 else (_YELLOW if seconds_left <= 10 else "")
    reset = _RESET if colour else ""

    sys.stdout.write(
        f"\r  {translate_message(label)}: {colour}[{bar}] {seconds_left:2d}s{reset}   "
    )
    sys.stdout.flush()


def clear_timer() -> None:
    """Erase the timer line."""
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()

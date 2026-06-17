"""Console display helpers: render the game state to the terminal."""

from __future__ import annotations

import os
import sys

from common.constants import SUIT_SYMBOLS
from common.models import Card, GameState

_RESET = "\033[0m"
_RED = "\033[91m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_YELLOW = "\033[93m"


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
        return "    -"
    return "\n".join(f"    [{i:2}] {card_str(c)}" for i, c in enumerate(hand, 1))


def render_table(attack_cards: list[Card], defense_cards: dict, trump_suit: str) -> str:
    """Render the table with 1-based attack slots and their defenders."""
    trump_sym = SUIT_SYMBOLS.get(trump_suit, "?")
    lines = [f"  Trump: {_BOLD}{trump_sym} {trump_suit}{_RESET}", "  Table:"]
    if not attack_cards:
        lines.append("    -")
        return "\n".join(lines)
    for i, atk in enumerate(attack_cards):
        dfn = defense_cards.get(str(i)) or defense_cards.get(i)
        if dfn:
            lines.append(f"    [{i + 1}] {card_str(atk)}  ->  {card_str(dfn)}")
        else:
            lines.append(f"    [{i + 1}] {card_str(atk)}  {_YELLOW}<- open{_RESET}")
    return "\n".join(lines)


def render_players(state: GameState, my_id: int) -> str:
    """Render the player roster with roles, hand sizes and turn markers."""
    lines = ["  Players:"]
    for p in state.players:
        you = f" {_YELLOW}<- YOU{_RESET}" if p.player_id == my_id else ""
        out = "" if p.is_active else f" {_DIM}[out]{_RESET}"
        role = p.role or "?"
        lines.append(f"    {p.name:15} | {role:8} | {p.hand_size}{out}{you}")
    return "\n".join(lines)


def render_state(state: GameState, my_id: int) -> None:
    """Clear the screen and print the full game state."""
    clear_screen()
    print("=" * 60)
    print(f"  {_BOLD}KING AND SERVANT{_RESET}   Round {state.round_number}")
    print("=" * 60)
    print(render_players(state, my_id))
    print()
    print(render_table(state.table_attack, state.table_defense, state.trump_suit))
    print()
    print("  Your hand:")
    print(render_hand_numbered(state.your_hand))
    if state.message:
        print(f"\n  {_YELLOW}>> {state.message}{_RESET}")
    print("=" * 60)


def print_timer(label: str, seconds_left: int, total: int = 60) -> None:
    """Print an in-place countdown bar using a carriage return."""
    bar_len = 20
    filled = int(bar_len * seconds_left / total) if total else 0
    bar = "#" * filled + "." * (bar_len - filled)
    colour = _RED if seconds_left <= 5 else (_YELLOW if seconds_left <= 10 else "")
    reset = _RESET if colour else ""
    sys.stdout.write(f"\r  {label}: {colour}[{bar}] {seconds_left:2d}s{reset}   ")
    sys.stdout.flush()


def clear_timer() -> None:
    """Erase the timer line."""
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()

"""Tests for parsing raw player input and building menus."""

from client.input_handler import (
    format_attack_hint,
    format_defense_hint,
    format_swap_menu,
    format_trump_menu,
    most_common_suit,
    parse_attack,
    parse_defense,
    parse_swap_choice,
    parse_trump_choice,
    suits_in_hand,
)
from common.models import Card


# --- trump -----------------------------------------------------------------

def test_suits_in_hand_order():
    hand = [Card("6", "clubs"), Card("A", "hearts"), Card("K", "clubs")]
    assert suits_in_hand(hand) == ["hearts", "clubs"]


def test_parse_trump_choice_valid():
    assert parse_trump_choice("2", ["spades", "hearts"]) == "hearts"


def test_parse_trump_choice_invalid():
    assert parse_trump_choice("9", ["spades"]) is None
    assert parse_trump_choice("x", ["spades"]) is None


def test_most_common_suit():
    hand = [Card("6", "clubs"), Card("7", "clubs"), Card("A", "hearts")]
    assert most_common_suit(hand) == "clubs"
    assert most_common_suit([]) == "spades"


def test_format_trump_menu_nonempty():
    assert "spades" in format_trump_menu(["spades"], [Card("K", "spades")])


# --- swap ------------------------------------------------------------------

def test_parse_swap_choice_skip():
    assert parse_swap_choice("0", [{"id": 3, "name": "Bob"}]) == "skip"


def test_parse_swap_choice_target():
    others = [{"id": 3, "name": "Bob"}, {"id": 5, "name": "Cara"}]
    assert parse_swap_choice("2", others) == 5


def test_parse_swap_choice_invalid():
    assert parse_swap_choice("9", [{"id": 3, "name": "Bob"}]) is None
    assert parse_swap_choice("x", [{"id": 3, "name": "Bob"}]) is None


def test_format_swap_menu_nonempty():
    assert "Bob" in format_swap_menu([{"id": 3, "name": "Bob", "role": "Ace"}])


# --- attack ----------------------------------------------------------------

def test_parse_attack_pass():
    assert parse_attack("0", [Card("6", "spades")]) == "pass"


def test_parse_attack_valid():
    hand = [Card("6", "spades"), Card("7", "hearts"), Card("8", "clubs")]
    assert parse_attack("1 3", hand) == [hand[0], hand[2]]


def test_parse_attack_invalid():
    hand = [Card("6", "spades")]
    assert parse_attack("9", hand) is None       # out of range
    assert parse_attack("1 1", hand) is None      # duplicate
    assert parse_attack("x", hand) is None        # non-numeric
    assert parse_attack("", hand) is None         # empty


def test_format_attack_hint_nonempty():
    assert format_attack_hint() != ""


# --- defense ---------------------------------------------------------------

def test_parse_defense_take():
    assert parse_defense("0", [], [Card("6", "spades")], {}) == "take"


def test_parse_defense_valid_pair():
    hand = [Card("K", "spades")]
    table_attack = [Card("6", "spades")]
    result = parse_defense("1-1", hand, table_attack, {})
    assert result == [(0, hand[0])]


def test_parse_defense_invalid():
    hand = [Card("K", "spades")]
    table_attack = [Card("6", "spades")]
    assert parse_defense("1", hand, table_attack, {}) is None        # not a pair
    assert parse_defense("9-1", hand, table_attack, {}) is None       # bad slot
    assert parse_defense("1-9", hand, table_attack, {}) is None       # bad hand idx
    # slot already beaten
    beaten = {"0": Card("A", "spades")}
    assert parse_defense("1-1", hand, table_attack, beaten) is None


def test_format_defense_hint_nonempty():
    assert format_defense_hint() != ""

"""Tests for parsing raw player input."""

from client.input_handler import parse_card_indices, parse_suit
from common.constants import SUITS


def test_parse_valid_indices():
    indices, err = parse_card_indices("0 2 3", hand_size=5)
    assert indices == [0, 2, 3]
    assert err == ""


def test_parse_single_index():
    indices, err = parse_card_indices("1", hand_size=5)
    assert indices == [1]
    assert err == ""


def test_parse_empty_input():
    indices, err = parse_card_indices("   ", hand_size=5)
    assert indices is None
    assert err != ""


def test_parse_non_numeric():
    indices, err = parse_card_indices("0 x 2", hand_size=5)
    assert indices is None
    assert err != ""


def test_parse_out_of_range():
    indices, err = parse_card_indices("0 9", hand_size=5)
    assert indices is None
    assert err != ""


def test_parse_duplicate_index():
    indices, err = parse_card_indices("1 1", hand_size=5)
    assert indices is None
    assert err != ""


def test_parse_suit_by_name():
    suit, err = parse_suit("hearts")
    assert suit == "hearts"
    assert err == ""


def test_parse_suit_by_index():
    suit, err = parse_suit("0")
    assert suit == SUITS[0]
    assert err == ""


def test_parse_suit_empty():
    suit, err = parse_suit("  ")
    assert suit is None
    assert err != ""


def test_parse_suit_invalid_name():
    suit, err = parse_suit("wands")
    assert suit is None
    assert err != ""


def test_parse_suit_index_out_of_range():
    suit, err = parse_suit("9")
    assert suit is None
    assert err != ""

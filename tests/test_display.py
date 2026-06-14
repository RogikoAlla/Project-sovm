"""Tests for the client terminal rendering helpers."""

from client import display
from common.models import Card


def test_render_card():
    assert display.render_card(Card("K", "spades")) == "K♠"


def test_render_hand_numbers_cards():
    out = display.render_hand([Card("6", "clubs"), Card("A", "hearts")])
    assert "[0]" in out and "[1]" in out
    assert "6♣" in out and "A♥" in out


def test_render_hand_empty():
    assert display.render_hand([]) != ""

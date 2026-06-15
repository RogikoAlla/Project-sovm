"""Tests for the client terminal rendering helpers."""

from client import display
from common.models import Card, GameState, PlayerInfo


def _state(**kwargs):
    base = dict(
        players=[PlayerInfo(player_id=0, name="Alice", role="King", hand_size=5)],
        your_hand=[Card("K", "spades")],
        trump_suit="hearts",
        deck_size=36,
    )
    base.update(kwargs)
    return GameState(**base)


def test_render_card():
    assert display.render_card(Card("K", "spades")) == "K♠"


def test_render_hand_numbers_cards():
    out = display.render_hand([Card("6", "clubs"), Card("A", "hearts")])
    assert "[0]" in out and "[1]" in out
    assert "6♣" in out and "A♥" in out


def test_render_hand_empty():
    assert display.render_hand([]) != ""


def test_render_table_empty():
    assert display.render_table(_state(table_attack=[])) != ""


def test_render_table_with_pair():
    state = _state(
        table_attack=[Card("6", "spades")],
        table_defense={0: Card("K", "spades")},
    )
    out = display.render_table(state)
    assert "6♠" in out and "K♠" in out and "->" in out


def test_render_table_undefended():
    state = _state(table_attack=[Card("6", "spades")], table_defense={})
    out = display.render_table(state)
    assert "6♠" in out and "?" in out

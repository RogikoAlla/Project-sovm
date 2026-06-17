"""Tests for the client terminal rendering helpers."""

from client import display
from common.models import Card, GameState, PlayerInfo


def _state(**kwargs):
    base = dict(
        players=[
            PlayerInfo(player_id=0, name="Alice", role="King", hand_size=5),
            PlayerInfo(player_id=1, name="Bob", role="Servant", hand_size=3),
        ],
        your_hand=[Card("K", "spades")],
        trump_suit="hearts",
        deck_size=36,
        round_number=2,
    )
    base.update(kwargs)
    return GameState(**base)


def test_card_str_contains_label():
    out = display.card_str(Card("K", "spades"))
    assert "K♠" in out


def test_render_hand_numbered():
    out = display.render_hand_numbered([Card("6", "clubs"), Card("A", "hearts")])
    assert "[ 1]" in out and "[ 2]" in out
    assert "6♣" in out and "A♥" in out


def test_render_hand_numbered_empty():
    assert display.render_hand_numbered([]) != ""


def test_render_table_empty():
    out = display.render_table([], {}, "hearts")
    assert "hearts" in out


def test_render_table_with_defense():
    out = display.render_table(
        [Card("6", "spades")], {"0": Card("K", "spades")}, "hearts"
    )
    assert "6♠" in out and "K♠" in out and "->" in out


def test_render_table_open_card():
    out = display.render_table([Card("6", "spades")], {}, "hearts")
    assert "6♠" in out and "open" in out


def test_render_players_marks_you_and_roles():
    out = display.render_players(_state(), my_id=0)
    assert "Alice" in out and "Bob" in out
    assert "King" in out and "Servant" in out
    assert "YOU" in out


def test_render_state_prints_round(capsys):
    display.render_state(_state(round_number=2), my_id=0)
    out = capsys.readouterr().out
    assert "Round 2" in out
    assert "Alice" in out

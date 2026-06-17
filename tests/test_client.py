"""Tests for the interactive game client."""

from client.client import GameClient
from common.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MSG_GAME_STATE,
)
from common.models import Card, GameState, PlayerInfo


def _state():
    return GameState(
        players=[
            PlayerInfo(player_id=0, name="Alice", role="King", hand_size=5),
            PlayerInfo(player_id=1, name="Bob", role="Servant", hand_size=3),
        ],
        your_hand=[Card("K", "spades")],
        trump_suit="hearts",
        deck_size=36,
        round_number=2,
    )


def test_defaults():
    client = GameClient()
    assert client.host == DEFAULT_HOST
    assert client.port == DEFAULT_PORT
    assert client.player_id == -1


def test_on_start_sets_player_id():
    client = GameClient(player_name="Bob")
    client._on_start({"players": [{"id": 0, "name": "Alice"}, {"id": 1, "name": "Bob"}]})
    assert client.player_id == 1


def test_dispatch_game_state_stores_state():
    client = GameClient()
    client._prompting = True  # avoid clearing the screen via render_state
    client._dispatch(MSG_GAME_STATE, _state().to_dict())
    assert client.current_state is not None
    assert client.current_state.round_number == 2


def test_on_round_end_prints(capsys):
    client = GameClient()
    client._on_round_end({"roles": {"0": "King", "1": "Servant"}})
    out = capsys.readouterr().out
    assert "King" in out and "Servant" in out


def test_on_game_end_prints(capsys):
    client = GameClient()
    client._on_game_end({"final_roles": {"0": "Loser"}})
    out = capsys.readouterr().out
    assert "Loser" in out

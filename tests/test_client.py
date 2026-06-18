"""Tests for the interactive game client."""

import asyncio

from client.client import GameClient
from common.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MSG_DECLARE_TRUMP,
    MSG_DONE,
    MSG_ERROR,
    MSG_GAME_STATE,
    MSG_PLAY_CARD,
    MSG_TAKE,
    MSG_THROW,
)
from common.models import Card, GameState, PlayerInfo
from common.protocol import decode_message


class FakeWriter:
    """Captures bytes written instead of sending them over a socket."""

    def __init__(self):
        self.sent = b""

    def write(self, data):
        self.sent += data

    async def drain(self):
        pass


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


def _ready(client, *lines):
    """Wire up loop, input queue and a fake writer with queued input."""
    client._loop = asyncio.get_event_loop()
    client._input_queue = asyncio.Queue()
    for line in lines:
        client._input_queue.put_nowait(line)
    client._writer = FakeWriter()
    client._drain_input = lambda: None  # keep pre-queued test input


def _last_sent(client):
    """Decode the last framed message written to the fake writer."""
    return decode_message(client._writer.sent.decode().strip())


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


def test_dispatch_error_prints(capsys):
    client = GameClient()
    client._dispatch(MSG_ERROR, "boom")
    assert "boom" in capsys.readouterr().out


def test_dispatch_timer_prints(capsys):
    client = GameClient()
    client._dispatch(MSG_PLAY_CARD, {"action": "timer", "label": "Turn", "seconds_left": 5})
    assert "Turn" in capsys.readouterr().out


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


def test_send_encodes_message():
    async def go():
        client = GameClient()
        client._writer = FakeWriter()
        await client._send(MSG_DONE)
        assert _last_sent(client)[0] == MSG_DONE

    asyncio.run(go())


def test_drain_input_empties_queue():
    async def go():
        client = GameClient()
        client._input_queue = asyncio.Queue()
        client._input_queue.put_nowait("stale")
        client._drain_input()
        assert client._input_queue.empty()

    asyncio.run(go())


def test_read_line_returns_value():
    async def go():
        client = GameClient()
        client._input_queue = asyncio.Queue()
        client._input_queue.put_nowait("hi")
        assert await client._read_line(1) == "hi"

    asyncio.run(go())


def test_read_line_timeout_returns_none():
    async def go():
        client = GameClient()
        client._input_queue = asyncio.Queue()
        assert await client._read_line(0.01) is None

    asyncio.run(go())


def test_prompt_loop_parses_valid():
    async def go():
        client = GameClient()
        _ready(client, "bad", "ok")
        result = await client._prompt_loop(
            parse=lambda ln: ln if ln == "ok" else None,
            on_timeout=lambda: "timeout",
            invalid_msg="x",
        )
        assert result == "ok"

    asyncio.run(go())


def test_prompt_loop_times_out():
    async def go():
        client = GameClient()
        _ready(client)
        result = await client._prompt_loop(
            parse=lambda ln: None,
            on_timeout=lambda: "timeout",
            invalid_msg="x",
            timeout=0.01,
        )
        assert result == "timeout"

    asyncio.run(go())


def test_do_declare_trump_sends_suit():
    async def go():
        client = GameClient()
        client.player_id = 0
        client.current_state = _state(your_hand=[Card("K", "spades")])
        _ready(client, "1")
        await client._do_declare_trump()
        assert _last_sent(client) == (MSG_DECLARE_TRUMP, {"suit": "spades"})

    asyncio.run(go())


def test_do_attack_pass_sends_done():
    async def go():
        client = GameClient()
        client.player_id = 0
        client.current_state = _state(your_hand=[Card("6", "spades")])
        _ready(client, "0")
        await client._do_attack()
        assert _last_sent(client)[0] == MSG_DONE

    asyncio.run(go())


def test_do_attack_plays_card_sends_throw():
    async def go():
        client = GameClient()
        client.player_id = 0
        client.current_state = _state(your_hand=[Card("6", "spades")])
        _ready(client, "1")
        await client._do_attack()
        assert _last_sent(client)[0] == MSG_THROW

    asyncio.run(go())


def test_do_defense_take_sends_take():
    async def go():
        client = GameClient()
        client.player_id = 1
        client.current_state = _state(
            your_hand=[Card("K", "spades")],
            table_attack=[Card("6", "spades")],
        )
        _ready(client, "0")
        await client._do_defense()
        assert _last_sent(client)[0] == MSG_TAKE

    asyncio.run(go())


def test_do_swap_offer_skip_sends_done():
    async def go():
        client = GameClient()
        client.player_id = 0
        client.current_state = _state()
        _ready(client, "0")
        await client._do_swap_offer()
        assert _last_sent(client)[0] == MSG_DONE

    asyncio.run(go())

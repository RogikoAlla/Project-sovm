"""Tests for the client wire-framing layer."""

import asyncio

from client.client import GameClient, render_message
from common.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MSG_ERROR,
    MSG_GAME_END,
    MSG_JOIN,
    MSG_ROUND_END,
)
from common.protocol import decode_message, encode_message


class FakeWriter:
    """Captures bytes written instead of sending them over a socket."""

    def __init__(self):
        self.sent = b""

    def write(self, data):
        self.sent += data

    async def drain(self):
        pass

    def close(self):
        self.closed = True


class FakeReader:
    """Returns a preset byte payload once, then EOF."""

    def __init__(self, data=b""):
        self._data = data

    async def read(self, _n):
        data, self._data = self._data, b""
        return data


def test_defaults():
    client = GameClient()
    assert client.host == DEFAULT_HOST
    assert client.port == DEFAULT_PORT


def test_encode_roundtrip():
    client = GameClient()
    data = client.encode(MSG_JOIN, {"name": "Alice"})
    messages = client.feed(data)
    assert messages == [(MSG_JOIN, {"name": "Alice"})]


def test_feed_handles_multiple_messages():
    client = GameClient()
    data = encode_message("A", 1) + encode_message("B", 2)
    messages = client.feed(data)
    assert messages == [("A", 1), ("B", 2)]


def test_feed_buffers_partial_message():
    client = GameClient()
    data = encode_message("PING", "hello")
    # Split the bytes mid-message: nothing complete yet.
    assert client.feed(data[:5]) == []
    # The rest arrives and the full message is decoded.
    assert client.feed(data[5:]) == [("PING", "hello")]


def test_join_sends_name():
    client = GameClient()
    client._writer = FakeWriter()
    asyncio.run(client.join("Alice"))
    assert decode_message(client._writer.sent.decode().strip()) == (
        MSG_JOIN,
        {"name": "Alice"},
    )


def test_receive_decodes_socket_data():
    client = GameClient()
    client._reader = FakeReader(encode_message("PING", 1))
    assert asyncio.run(client.receive()) == [("PING", 1)]


def test_receive_returns_empty_on_eof():
    client = GameClient()
    client._reader = FakeReader(b"")
    assert asyncio.run(client.receive()) == []


def test_render_message_round_and_game_end():
    assert render_message(MSG_ROUND_END, "winner") is not None
    assert render_message(MSG_GAME_END, "done") is not None


def test_render_message_error():
    assert "boom" in render_message(MSG_ERROR, "boom")


def test_render_message_unknown_returns_none():
    assert render_message("SOMETHING_ELSE", {}) is None

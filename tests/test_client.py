"""Tests for the client wire-framing layer."""

from client.client import GameClient
from common.constants import DEFAULT_HOST, DEFAULT_PORT, MSG_JOIN
from common.protocol import encode_message


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

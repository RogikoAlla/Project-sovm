"""Tests for the client command-line entry point."""

import asyncio

from client.main import build_parser, run
from common.constants import DEFAULT_HOST, DEFAULT_PORT


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.host == DEFAULT_HOST
    assert args.port == DEFAULT_PORT
    assert args.name == "Player"


def test_parser_custom_values():
    args = build_parser().parse_args(["--host", "1.2.3.4", "--port", "9", "--name", "Bob"])
    assert args.host == "1.2.3.4"
    assert args.port == 9
    assert args.name == "Bob"


class FakeClient:
    """Records calls and returns preset message batches from receive()."""

    def __init__(self, batches):
        self._batches = list(batches)
        self.joined = None
        self.connected = False
        self.closed = False

    async def connect(self):
        self.connected = True

    async def join(self, name):
        self.joined = name

    async def receive(self):
        return self._batches.pop(0) if self._batches else []

    async def close(self):
        self.closed = True


def test_run_joins_and_stops_on_eof(capsys):
    client = FakeClient([[("ERROR", "boom")], []])
    asyncio.run(run(client, "Alice"))

    assert client.connected is True
    assert client.joined == "Alice"
    assert client.closed is True
    assert "boom" in capsys.readouterr().out

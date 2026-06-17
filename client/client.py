"""Networking skeleton for the King and Servant client. """

from __future__ import annotations

import asyncio
from typing import Any

from client import display
from common.constants import (
    BUFFER_SIZE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    ENCODING,
    MSG_ERROR,
    MSG_GAME_END,
    MSG_GAME_STATE,
    MSG_JOIN,
    MSG_ROUND_END,
)
from common.i18n import get_translator
from common.models import GameState
from common.protocol import decode_message, encode_message, split_frames

_ = get_translator()


class GameClient:
    """Holds connection settings and the incoming byte buffer."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._buffer = ""
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    def encode(self, msg_type: str, payload: Any = None) -> bytes:
        """Encode an outgoing message to bytes ready to send."""
        return encode_message(msg_type, payload)

    def feed(self, data: bytes) -> list[tuple[str, Any]]:
        """Buffer received bytes and return any complete decoded messages."""
        self._buffer += data.decode(ENCODING)
        frames, self._buffer = split_frames(self._buffer)
        return [decode_message(frame) for frame in frames]

    async def connect(self) -> None:
        """Open the TCP connection to the server."""
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

    async def send(self, msg_type: str, payload: Any = None) -> None:
        """Send a typed message over the open connection."""
        self._writer.write(self.encode(msg_type, payload))
        await self._writer.drain()

    async def join(self, name: str) -> None:
        """Send the JOIN handshake with the player's name."""
        await self.send(MSG_JOIN, {"name": name})

    async def receive(self) -> list[tuple[str, Any]]:
        """Read one chunk from the socket and return decoded messages."""
        data = await self._reader.read(BUFFER_SIZE)
        if not data:
            return []
        return self.feed(data)

    async def close(self) -> None:
        """Close the connection if it is open."""
        if self._writer is not None:
            self._writer.close()


def render_message(msg_type: str, payload: Any) -> str | None:
    """Turn a server message into text to display, or None if nothing to show."""
    if msg_type == MSG_GAME_STATE:
        return display.render_state(GameState.from_dict(payload))
    if msg_type == MSG_ROUND_END:
        return _("Round over.") + " " + str(payload or "")
    if msg_type == MSG_GAME_END:
        return _("Game over.") + " " + str(payload or "")
    if msg_type == MSG_ERROR:
        return _("Error:") + " " + str(payload or "")
    return None

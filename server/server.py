"""Asyncio TCP server for King and Servant."""

import asyncio
import logging

from common.constants import (
    ENCODING,
)
from common.protocol import decode_message, encode_message, split_frames

logger = logging.getLogger(__name__)


class ClientConnection:
    """Wraps a single asyncio client connection.

    Args:
        reader: Asyncio stream reader.
        writer: Asyncio stream writer.
        player_id: Assigned integer ID.
    """

    def __init__(self, reader, writer, player_id: int) -> None:
        """Store reader/writer and player identifier."""
        self.reader = reader
        self.writer = writer
        self.player_id = player_id
        self.name: str = f"Player{player_id}"
        self._buffer: str = ""

    async def send(self, msg_type: str, payload=None) -> None:
        """Send a typed message to this client."""
        try:
            self.writer.write(encode_message(msg_type, payload))
            await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            logger.warning("Client %d disconnected", self.player_id)

    async def recv(self):
        """Read the next complete message from this client."""
        while True:
            frames, self._buffer = split_frames(self._buffer)
            if frames:
                return decode_message(frames[0])
            try:
                chunk = await self.reader.read(4096)
                if not chunk:
                    return None
                self._buffer += chunk.decode(ENCODING)
            except (ConnectionResetError, asyncio.IncompleteReadError):
                return None

    async def recv_timeout(self, seconds: int):
        """Receive with a timeout; returns None on timeout or disconnect."""
        try:
            return await asyncio.wait_for(self.recv(), timeout=seconds)
        except asyncio.TimeoutError:
            return None

    def close(self) -> None:
        """Close the underlying writer."""
        try:
            self.writer.close()
        except Exception:
            pass

"""Asyncio TCP server for King and Servant."""

import asyncio
import logging

from common.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DECK_36,
    ENCODING,
    MSG_JOIN,
    PLAYER_COUNT
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


class GameServer:
    """Top-level server: waits for 4 connections, then runs the game.

    Args:
        host: Bind address.
        port: TCP port.
        deck_size: 36 or 52.
    """

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, deck_size=DECK_36) -> None:
        """Initialize server configuration."""
        self.host = host
        self.port = port
        self.deck_size = deck_size
        self.connections: list[ClientConnection] = []
        self.engine = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start listening for connections."""
        server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        addr = server.sockets[0].getsockname()
        print(f"[Server] Waiting for {PLAYER_COUNT} players on {addr[0]}:{addr[1]}...")
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader, writer) -> None:
        """Accept a connection and wait for JOIN."""
        async with self._lock:
            pid = len(self.connections)
            if pid >= PLAYER_COUNT:
                writer.write(encode_message("ERROR", "Game is full"))
                await writer.drain()
                writer.close()
                return

            conn = ClientConnection(reader, writer, pid)
            msg = await conn.recv()
            if msg is None or msg[0] != MSG_JOIN:
                conn.close()
                return

            conn.name = (msg[1] or {}).get("name", conn.name)
            self.connections.append(conn)
            print(f"[Server] {conn.name} connected ({len(self.connections)}/{PLAYER_COUNT})")

            if len(self.connections) == PLAYER_COUNT:
                asyncio.create_task(self._run_game())

"""Asyncio TCP server for King and Servant."""

import asyncio
import logging
from typing import Optional

from common.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DECK_36,
    ENCODING,
    MSG_JOIN,
    MSG_GAME_STATE,
    MSG_PLAY_CARD,
    MSG_SWAP_DECK,
    MSG_DONE,
    PLAYER_COUNT
)
from common.protocol import decode_message, encode_message, split_frames

logger = logging.getLogger(__name__)

TURN_TIMEOUT = 60


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

    # ------------------------------------------------------------------
    # Broadcast helpers
    # ------------------------------------------------------------------

    async def _broadcast(self, msg_type: str, payload=None) -> None:
        """Send a message to all connected clients."""
        for conn in self.connections:
            await conn.send(msg_type, payload)

    async def _broadcast_state(self, message: str = "") -> None:
        """Push a personalised game state to every client."""
        assert self.engine is not None
        for conn in self.connections:
            state = self.engine.build_game_state(conn.player_id)
            state.message = message
            await conn.send(MSG_GAME_STATE, state.to_dict())

    async def _countdown(self, label: str, seconds: int) -> asyncio.Task:
        """Start a background task that broadcasts a per-second countdown.

        Args:
            label: Text shown next to the timer bar on clients.
            seconds: Number of seconds to count down.

        Returns:
            The running task (cancel it as soon as input arrives).
        """
        async def _run() -> None:
            for t in range(seconds, 0, -1):
                await self._broadcast(MSG_PLAY_CARD, {
                    "action": "timer",
                    "label": label,
                    "seconds_left": t,
                })
                await asyncio.sleep(1)

        return asyncio.create_task(_run())

    def _conn_by_role(self, role: str) -> Optional[ClientConnection]:
        """Find the connection whose player currently holds *role*."""
        assert self.engine is not None
        for p in self.engine.players:
            if p.role == role:
                return self._conn_by_id(p.player_id)
        return None

    def _conn_by_id(self, pid: int) -> Optional[ClientConnection]:
        """Find a connection by player ID."""
        for conn in self.connections:
            if conn.player_id == pid:
                return conn
        return None

    def _player_by_role(self, role: str):
        """Return the ServerPlayer currently holding *role* (or ``None``)."""
        assert self.engine is not None
        return next((p for p in self.engine.players if p.role == role), None)

    @staticmethod
    def _most_common_suit(hand) -> str:
        """Return the suit with the most cards in *hand* (fallback trump)."""
        counts: dict = {}
        for card in hand:
            counts[card.suit] = counts.get(card.suit, 0) + 1
        return max(counts, key=lambda s: counts[s]) if counts else "spades"

    # ------------------------------------------------------------------
    # Game flow
    # ------------------------------------------------------------------

    async def _run_game(self) -> None:
        """Run the full multi-round game session."""
        players = [ServerPlayer(player_id=c.player_id, name=c.name)
                   for c in self.connections]
        self.engine = GameEngine(players, self.deck_size)

        await self._broadcast(MSG_START, {
            "players": [{"id": p.player_id, "name": p.name} for p in players],
            "deck_size": self.deck_size,
        })

        round_num = 0
        while True:
            round_num += 1
            self.engine.deal()
            print(f"[Сервер] Раунд {round_num}")
            await self._play_round()
            await self._broadcast(MSG_ROUND_END, {
                "roles": {str(p.player_id): p.role for p in self.engine.players}
            })
            self.engine.end_round()

    async def _play_round(self) -> None:
        """One full round: pre-round pause → blind swap → trump → turns."""
        await self._phase_pre_round()
        await self._phase_king_swap()
        await self._phase_declare_trump()
        await self._phase_turns()

    async def _phase_pre_round(self) -> None:
        """Show dealt roles and hands, then count down 10 seconds before play."""
        await self._broadcast_state(
            "Новый раунд! Роли и руки розданы. Игра начнётся через 10 секунд..."
        )
        timer = await self._countdown("Старт раунда", 10)
        await timer


    # ------------------------------------------------------------------
    # Phase 1: King's blind swap
    # ------------------------------------------------------------------

    async def _phase_king_swap(self) -> None:
        """Offer the King a one-time blind hand swap (30s)."""
        assert self.engine is not None
        king_conn = self._conn_by_role(ROLE_KING)
        if king_conn is None:
            return

        # State message intentionally has no trump yet (not declared).
        await self._broadcast_state(
            f"Король {king_conn.name} решает: поменять руку вслепую? (60 сек)"
        )
        await king_conn.send(MSG_PLAY_CARD, {"action": "swap_offer"})

        timer = await self._countdown(f"Король {king_conn.name}: обмен рукой", TURN_TIMEOUT)
        msg = await king_conn.recv_timeout(TURN_TIMEOUT)
        timer.cancel()

        if msg and msg[0] == MSG_SWAP_DECK:
            target_id = int((msg[1] or {}).get("target_id", -1))
            ok, err = self.engine.king_blind_swap(king_conn.player_id, target_id)
            if ok:
                target = self._conn_by_id(target_id)
                tname = target.name if target else str(target_id)
                # Everyone sees who swapped with whom.
                await self._broadcast_state(
                    f"Король {king_conn.name} поменялся руками с {tname} (вслепую)!"
                )
            else:
                await self._broadcast_state(f"Обмен не состоялся: {err}")
        else:
            await self._broadcast_state(f"Король {king_conn.name} не стал меняться.")

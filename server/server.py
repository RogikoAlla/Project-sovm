"""Asyncio TCP server: accepts 4 players and manages the game session."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from common.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DECK_36,
    ENCODING,
    MSG_BEAT,
    MSG_DECLARE_TRUMP,
    MSG_DONE,
    MSG_ERROR,
    MSG_GAME_STATE,
    MSG_JOIN,
    MSG_PLAY_CARD,
    MSG_ROUND_END,
    MSG_START,
    MSG_SWAP_DECK,
    MSG_TAKE,
    MSG_THROW,
    PLAYER_COUNT,
    ROLE_ACE,
    ROLE_KING,
    ROLE_QUEEN,
    ROLE_SERVANT,
    SUIT_SYMBOLS,
)
from common.models import Card
from common.protocol import decode_message, encode_message, split_frames
from server.game_engine import GameEngine, ServerPlayer

logger = logging.getLogger(__name__)

TURN_TIMEOUT = 60  # server-side limit (clients use a slightly shorter 58s)


class ClientConnection:
    """Wraps a single asyncio client connection."""

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
        """Receive with a timeout; returns ``None`` on timeout/disconnect."""
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
    """Top-level server: waits for 4 connections, then runs the game."""

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, deck_size=DECK_36) -> None:
        """Initialize server configuration."""
        self.host = host
        self.port = port
        self.deck_size = deck_size
        self.connections: list[ClientConnection] = []
        self.engine: Optional[GameEngine] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start listening for connections."""
        server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        addr = server.sockets[0].getsockname()
        print(f"[Server] Waiting for {PLAYER_COUNT} players at {addr[0]}:{addr[1]}...")
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader, writer) -> None:
        """Accept a connection and wait for JOIN."""
        async with self._lock:
            pid = len(self.connections)
            if pid >= PLAYER_COUNT:
                writer.write(encode_message(MSG_ERROR, "Game is full"))
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
            print(f"[Server] Round {round_num}")
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
            "New round! Roles and hands have been dealt. The game starts in 10 seconds..."
        )
        timer = await self._countdown("Round start", 10)
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
            f"King {king_conn.name} is deciding whether to blindly swap hands. (60 sec)"
        )
        await king_conn.send(MSG_PLAY_CARD, {"action": "swap_offer"})

        timer = await self._countdown(f"King {king_conn.name}: hand swap", TURN_TIMEOUT)
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
                    f"King {king_conn.name} blindly swapped hands with {tname}!"
                )
            else:
                await self._broadcast_state(f"The exchange did not take place: {err}")
        else:
            await self._broadcast_state(f"King {king_conn.name} chose not to swap.")

    # ------------------------------------------------------------------
    # Phase 2: trump declaration
    # ------------------------------------------------------------------

    async def _phase_declare_trump(self) -> None:
        """King picks the trump suit from his own hand (30s)."""
        assert self.engine is not None
        king_conn = self._conn_by_role(ROLE_KING)
        if king_conn is None:
            self.engine.declare_trump("spades")
            return

        await self._broadcast_state(
            f"King {king_conn.name} is choosing a trump suit from their cards. (60 sec)..."
        )
        await king_conn.send(MSG_PLAY_CARD, {"action": "declare_trump"})

        timer = await self._countdown(f"King {king_conn.name}: trump selection", TURN_TIMEOUT)
        msg = await king_conn.recv_timeout(TURN_TIMEOUT)
        timer.cancel()

        suit = None
        if msg and msg[0] == MSG_DECLARE_TRUMP:
            suit = (msg[1] or {}).get("suit")

        if not suit or not self.engine.declare_trump(suit):
            king_player = self._player_by_role(ROLE_KING)
            suit = self._most_common_suit(king_player.hand if king_player else [])
            self.engine.declare_trump(suit)
            sym = SUIT_SYMBOLS.get(suit, suit)
            await self._broadcast_state(
                f"Trump was selected automatically: {sym} {suit}"
            )
        else:
            sym = SUIT_SYMBOLS.get(suit, suit)
            # Everyone sees the chosen trump.
            await self._broadcast_state(
                f"King {king_conn.name} declared trump: {sym} {suit}!"
            )

    # ------------------------------------------------------------------
    # Phase 3: main turns
    # ------------------------------------------------------------------

    async def _phase_turns(self) -> None:
        """Run cyclic attack/defense exchanges until the round ends.

        The attack order (Servant → Queen → Ace → King → Servant …) only
        includes players who still have cards.  If a role's holder has run
        out, that slot is skipped and the previous attacker goes directly to
        the next active defender.  Example: if the Queen has no cards,
        the Servant attacks the Ace.
        """
        assert self.engine is not None

        # Canonical clockwise order of roles.
        role_order = [ROLE_SERVANT, ROLE_QUEEN, ROLE_ACE, ROLE_KING]

        # Index into role_order for the current attacker.
        atk_pos = 0

        for _ in range(200):  # safety bound
            if self.engine.is_round_over():
                break

            # Build the list of roles whose holders still have cards.
            active_roles = [
                r for r in role_order
                if (p := self._player_by_role(r)) and p.hand
            ]
            if len(active_roles) < 2:
                break

            # Wrap attacker position into active list.
            atk_pos = atk_pos % len(active_roles)
            atk_role = active_roles[atk_pos]

            # Defender is the next active role clockwise.
            def_role = active_roles[(atk_pos + 1) % len(active_roles)]

            await self._run_exchange(atk_role, def_role)

            # After the exchange recalculate active roles — someone may have
            # run out of cards — then advance to the next attacker.
            active_roles = [
                r for r in role_order
                if (p := self._player_by_role(r)) and p.hand
            ]
            if active_roles:
                # Move to the role that follows def_role in the active list.
                if def_role in active_roles:
                    atk_pos = active_roles.index(def_role)
                else:
                    atk_pos = (atk_pos + 1) % len(active_roles)

    async def _run_exchange(self, atk_role: str, def_role: str) -> str:
        """Run a single attacker→defender exchange (full Durak rules).

        Args:
            atk_role: Role of the attacker for this exchange.
            def_role: Role of the defender for this exchange.

        Returns:
            ``'beat'`` (defender survived), ``'took'`` (defender picked up),
            or ``'skip'`` (no playable attacker/defender or attacker passed).
        """
        assert self.engine is not None
        atk_player = self._player_by_role(atk_role)
        def_player = self._player_by_role(def_role)
        atk_conn = self._conn_by_role(atk_role)
        def_conn = self._conn_by_role(def_role)

        if not (atk_player and atk_player.hand and def_player and def_player.hand
                and atk_conn is not None and def_conn is not None):
            return "skip"

        self.engine.set_attacker_defender(atk_player.player_id, def_player.player_id)

        # Initial attack — the attacker may decline (pass) on an empty table.
        if await self._prompt_attack(atk_conn, def_conn, atk_role, def_role, True) != "played":
            return "skip"

        while True:
            # Defender beats everything or takes.
            if await self._defender_turn(def_conn) == "took":
                return "took"

            if self.engine.is_round_over():
                self.engine.defender_done()
                return "beat"

            # All current cards are beaten — attacker may подкинуть or бито.
            more = await self._prompt_attack(atk_conn, def_conn, atk_role, def_role, False)
            if more != "played":
                ok, _ = self.engine.defender_done()
                await self._broadcast_state(
                    f"{atk_conn.name} declared BEAT. The table is cleared."
                )
                return "beat"
            # Otherwise loop: the defender must now beat the newly added cards.

    async def _prompt_attack(
        self, atk_conn: ClientConnection, def_conn: ClientConnection,
        atk_role: str, def_role: str, initial: bool,
    ) -> str:
        """Prompt the attacker to play/add cards, re-prompting on invalid input.

        Args:
            atk_conn: Attacker connection.
            def_conn: Defender connection.
            atk_role: Attacker's role label.
            def_role: Defender's role label.
            initial: ``True`` for the opening attack, ``False`` for подкидывание.

        Returns:
            ``'played'`` if cards were placed, else ``'done'`` (pass / бито).
        """
        assert self.engine is not None
        while True:
            if initial:
                label = f"Attack: {atk_conn.name} ({atk_role}) -> {def_conn.name} ({def_role})"
            else:
                label = (
                    f"{atk_conn.name}: you may throw in cards of the same ranks "
                    "or declare beat"
                )
            await self._broadcast_state(label)
            await atk_conn.send(MSG_PLAY_CARD, {"action": "attack", "initial": initial})

            timer = await self._countdown(f"Turn: {atk_conn.name}", TURN_TIMEOUT)
            msg = await atk_conn.recv_timeout(TURN_TIMEOUT)
            timer.cancel()

            if msg is None or msg[0] == MSG_DONE:
                return "done"
            if msg[0] == MSG_THROW:
                cards = [Card.from_dict(c) for c in (msg[1] or {}).get("cards", [])]
                ok, err = self.engine.apply_attack_batch(atk_conn.player_id, cards)
                if not ok:
                    await atk_conn.send(MSG_ERROR, err)
                    continue
                shown = ", ".join(str(c) for c in cards)
                await self._broadcast_state(f"{atk_conn.name} puts on the table: {shown}")
                return "played"
            return "done"

    async def _defender_turn(self, def_conn: ClientConnection) -> str:
        """Resolve the defender's response, looping until beaten or taken.

        The defender may submit one or more ``slot-card`` pairs; the loop
        re-prompts for any cards still undefended and ends when every attack
        card is beaten or the defender takes them all.

        Returns:
            ``'beat'`` if everything was defended, ``'took'`` otherwise.
        """
        assert self.engine is not None
        while True:
            undefended = self.engine.undefended_indices()
            if not undefended:
                return "beat"

            await self._broadcast_state(
                f"{def_conn.name} is defending - {len(undefended)} left to beat"
            )
            await def_conn.send(MSG_PLAY_CARD, {"action": "defense"})

            timer = await self._countdown(f"Defense: {def_conn.name}", TURN_TIMEOUT)
            msg = await def_conn.recv_timeout(TURN_TIMEOUT)
            timer.cancel()

            if msg is None or msg[0] == MSG_TAKE:
                self.engine.defender_takes(def_conn.player_id)
                await self._broadcast_state(f"{def_conn.name} takes the cards!")
                return "took"

            if msg[0] == MSG_BEAT:
                error = None
                for pair in (msg[1] or {}).get("pairs", []):
                    atk_idx = int(pair["attack_idx"])
                    card = Card.from_dict(pair["card"])
                    ok, err = self.engine.play_defense_card(
                        def_conn.player_id, atk_idx, card
                    )
                    if not ok:
                        error = err
                        break
                if error:
                    await def_conn.send(MSG_ERROR, error)
                # Loop: finished → 'beat' at top, or re-prompt remaining cards.
            else:
                self.engine.defender_takes(def_conn.player_id)
                await self._broadcast_state(f"{def_conn.name} takes the cards!")
                return "took"

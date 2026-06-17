"""Asyncio TCP client: connects to the server and drives the console UI.

A single background thread reads stdin lines into an asyncio.Queue, so the
socket reader never blocks on user input and prompts have real deadlines.
"""

from __future__ import annotations

import asyncio
import builtins
import logging
import sys
import threading
from typing import Callable, Optional

from client.display import clear_timer, print_timer, render_state
from client.input_handler import (
    format_attack_hint,
    format_defense_hint,
    format_swap_menu,
    format_trump_menu,
    most_common_suit,
    parse_attack,
    parse_defense,
    parse_swap_choice,
    parse_trump_choice,
    suits_in_hand,
)
from common.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    ENCODING,
    MSG_BEAT,
    MSG_DECLARE_TRUMP,
    MSG_DONE,
    MSG_ERROR,
    MSG_GAME_END,
    MSG_GAME_STATE,
    MSG_JOIN,
    MSG_PLAY_CARD,
    MSG_ROUND_END,
    MSG_START,
    MSG_SWAP_DECK,
    MSG_TAKE,
    MSG_THROW,
)
from common.i18n import setup_i18n
from common.models import GameState
from common.protocol import decode_message, encode_message, split_frames

if not hasattr(builtins, "_"):
    setup_i18n()

logger = logging.getLogger(__name__)

CLIENT_TIMEOUT = 58  # local input deadline (shorter than the server's 60s)


class GameClient:
    """Connects to the game server and manages the interactive session."""

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, player_name="Player") -> None:
        """Store connection parameters."""
        self.host = host
        self.port = port
        self.player_name = player_name
        self.player_id: int = -1
        self.current_state: Optional[GameState] = None
        self._buffer: str = ""
        self._writer = None
        self._prompting: bool = False
        self._prompt_lock: Optional[asyncio.Lock] = None
        self._input_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self) -> None:
        """Connect to the server and run until disconnected."""
        reader, writer = await asyncio.open_connection(self.host, self.port)
        self._writer = writer
        self._loop = asyncio.get_event_loop()
        self._input_queue = asyncio.Queue()
        self._prompt_lock = asyncio.Lock()
        self._start_stdin_thread()
        try:
            await self._send(MSG_JOIN, {"name": self.player_name})
            await self._reader_task(reader)
        finally:
            writer.close()

    def _start_stdin_thread(self) -> None:
        """Launch the daemon thread that reads stdin into the queue."""
        loop = self._loop
        queue = self._input_queue

        def run() -> None:
            try:
                for line in sys.stdin:
                    loop.call_soon_threadsafe(queue.put_nowait, line.rstrip("\n"))
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()

    async def _send(self, msg_type: str, payload=None) -> None:
        """Encode and send a message to the server."""
        if self._writer is None:
            return
        self._writer.write(encode_message(msg_type, payload))
        await self._writer.drain()

    async def _reader_task(self, reader) -> None:
        """Continuously read and dispatch server messages."""
        print(f"  {_('Connected. Waiting for players...')} ({self.host}:{self.port})")
        while True:
            frames, self._buffer = split_frames(self._buffer)
            if not frames:
                chunk = await reader.read(4096)
                if not chunk:
                    print(f"\n  {_('Disconnected from server.')}")
                    return
                self._buffer += chunk.decode(ENCODING)
                continue
            for frame in frames:
                msg_type, payload = decode_message(frame)
                self._dispatch(msg_type, payload)

    def _dispatch(self, msg_type: str, payload) -> None:
        """Handle one decoded message without blocking the reader."""
        if msg_type == MSG_GAME_STATE:
            self.current_state = GameState.from_dict(payload)
            if not self._prompting:
                render_state(self.current_state, self.player_id)
        elif msg_type == MSG_PLAY_CARD:
            action = (payload or {}).get("action", "")
            if action == "timer":
                if not self._prompting:
                    print_timer(payload.get("label", ""), payload.get("seconds_left", 0))
            elif action:
                self._prompting = True
                asyncio.create_task(self._handle_prompt(action))
        elif msg_type == MSG_START:
            self._on_start(payload)
        elif msg_type == MSG_ROUND_END:
            self._on_round_end(payload)
        elif msg_type == MSG_GAME_END:
            self._on_game_end(payload)
        elif msg_type == MSG_ERROR:
            clear_timer()
            print(f"\n  [{_('Error')}] {payload}")

    async def _handle_prompt(self, action: str) -> None:
        """Run the appropriate interactive prompt for *action*."""
        async with self._prompt_lock:
            try:
                if action == "swap_offer":
                    await self._do_swap_offer()
                elif action == "declare_trump":
                    await self._do_declare_trump()
                elif action == "attack":
                    await self._do_attack()
                elif action == "defense":
                    await self._do_defense()
            finally:
                self._prompting = False

    def _drain_input(self) -> None:
        """Discard any keystrokes typed before this prompt began."""
        if self._input_queue is None:
            return
        while not self._input_queue.empty():
            try:
                self._input_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def _read_line(self, timeout: float) -> Optional[str]:
        """Return one line from the queue, or None on timeout."""
        try:
            return await asyncio.wait_for(self._input_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    async def _prompt_loop(
        self,
        parse: Callable[[str], object],
        on_timeout: Callable[[], object],
        invalid_msg: str,
        timeout: float = CLIENT_TIMEOUT,
    ) -> object:
        """Read and parse input until valid or the deadline passes."""
        assert self._loop is not None
        deadline = self._loop.time() + timeout
        sys.stdout.write("  > ")
        sys.stdout.flush()
        while True:
            remaining = deadline - self._loop.time()
            if remaining <= 0:
                return on_timeout()
            line = await self._read_line(remaining)
            if line is None:
                return on_timeout()
            result = parse(line)
            if result is not None:
                return result
            print(f"  {invalid_msg}")
            sys.stdout.write("  > ")
            sys.stdout.flush()

    async def _do_swap_offer(self) -> None:
        """Prompt the King to pick a swap target or skip."""
        if self.current_state is None:
            await self._send(MSG_DONE)
            return
        others = [
            {"id": p.player_id, "name": p.name, "role": p.role}
            for p in self.current_state.players
            if p.player_id != self.player_id
        ]
        self._drain_input()
        print(format_swap_menu(others))
        result = await self._prompt_loop(
            parse=lambda ln: parse_swap_choice(ln, others),
            on_timeout=lambda: "skip",
            invalid_msg=f"0..{len(others)}",
        )
        if isinstance(result, int):
            await self._send(MSG_SWAP_DECK, {"target_id": result})
        else:
            await self._send(MSG_DONE)

    async def _do_declare_trump(self) -> None:
        """Prompt the King to choose a trump suit from his own hand."""
        if self.current_state is None:
            return
        hand = self.current_state.your_hand
        suits = suits_in_hand(hand)
        self._drain_input()
        print(format_trump_menu(suits, hand))
        suit = await self._prompt_loop(
            parse=lambda ln: parse_trump_choice(ln, suits),
            on_timeout=lambda: most_common_suit(hand),
            invalid_msg=f"1..{len(suits)}",
        )
        await self._send(MSG_DECLARE_TRUMP, {"suit": suit})

    async def _do_attack(self) -> None:
        """Prompt the attacker to play one or more cards, or pass."""
        if self.current_state is None:
            return
        hand = self.current_state.your_hand
        self._drain_input()
        print(format_attack_hint())
        result = await self._prompt_loop(
            parse=lambda ln: parse_attack(ln, hand),
            on_timeout=lambda: "pass",
            invalid_msg=f"1..{len(hand)} | 0",
        )
        if result == "pass":
            await self._send(MSG_DONE)
        else:
            await self._send(MSG_THROW, {"cards": [c.to_dict() for c in result]})

    async def _do_defense(self) -> None:
        """Prompt the defender to beat cards in pairs or take all."""
        if self.current_state is None:
            return
        st = self.current_state
        self._drain_input()
        print(format_defense_hint())
        result = await self._prompt_loop(
            parse=lambda ln: parse_defense(
                ln, st.your_hand, st.table_attack, st.table_defense
            ),
            on_timeout=lambda: "take",
            invalid_msg="1-3 2-5 | 0",
        )
        if result == "take":
            await self._send(MSG_TAKE)
        else:
            await self._send(MSG_BEAT, {
                "pairs": [
                    {"attack_idx": atk_idx, "card": card.to_dict()}
                    for atk_idx, card in result
                ]
            })

    def _on_start(self, payload: dict) -> None:
        """Handle game start: learn our own player_id."""
        players = (payload or {}).get("players", [])
        print(f"\n  {_('Game started.')}\n")
        for p in players:
            if p["name"] == self.player_name:
                self.player_id = p["id"]

    def _on_round_end(self, payload: dict) -> None:
        """Print the round-end role summary."""
        roles = (payload or {}).get("roles", {})
        print(f"\n  {_('Round ended')}:")
        for pid, role in roles.items():
            print(f"    {pid}: {role}")

    def _on_game_end(self, payload: dict) -> None:
        """Print the final game result."""
        roles = (payload or {}).get("final_roles", {})
        print(f"\n  {_('Game over')}:")
        for pid, role in roles.items():
            print(f"    {pid}: {role}")

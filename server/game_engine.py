"""Core game engine: state machine for King and Servant rounds."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from common.constants import (
    CARDS_PER_PLAYER_36,
    CARDS_PER_PLAYER_52,
    DECK_36,
    PLAYER_COUNT,
    ROLE_QUEEN,
    ROLE_SERVANT,
    ROLES_CCW,
    SUITS,
)
from common.models import Card, PlayerInfo, build_deck


@dataclass
class ServerPlayer:
    """Server-side player state including the private hand."""

    player_id: int
    name: str
    role: Optional[str] = None
    hand: list[Card] = field(default_factory=list)
    is_active: bool = True

    def to_info(self) -> PlayerInfo:
        """Return a public-facing PlayerInfo (hand hidden as a count)."""
        return PlayerInfo(
            player_id=self.player_id,
            name=self.name,
            role=self.role,
            hand_size=len(self.hand),
            is_active=self.is_active,
        )

    def remove_card(self, card: Card) -> bool:
        """Remove card from hand if present."""
        try:
            self.hand.remove(card)
            return True
        except ValueError:
            return False


class GameEngine:
    """Manages a complete multi-round King and Servant session."""

    def __init__(self, players: list[ServerPlayer], deck_size: int = DECK_36) -> None:
        if len(players) != PLAYER_COUNT:
            raise ValueError(f"Exactly {PLAYER_COUNT} players required, got {len(players)}")
        self.players: list[ServerPlayer] = players
        self.deck_size: int = deck_size
        self.trump_suit: str = ""
        self.table_attack: list[Card] = []
        self.table_defense: dict[int, Card] = {}
        self.attacker_idx: int = 0
        self.defender_idx: int = 0
        self.king_swap_used: bool = False
        self.round_number: int = 1
        self._roles_assigned: bool = False

    def deal(self) -> None:
        """Shuffle and deal cards; assign roles based on the King of Spades."""
        self.trump_suit = ""
        self.king_swap_used = False
        self._clear_table()
        deck = build_deck(self.deck_size)
        per = CARDS_PER_PLAYER_36 if self.deck_size == DECK_36 else CARDS_PER_PLAYER_52
        for i, player in enumerate(self.players):
            player.hand = deck[i * per : (i + 1) * per]
            player.is_active = True
        if not self._roles_assigned:
            self._assign_initial_roles()
        self._set_attack_defense_from_roles()

    def _assign_initial_roles(self) -> None:
        """Assign roles based on who holds the King of Spades."""
        king_holder_idx = self._find_king_of_spades()
        for offset, role in enumerate(ROLES_CCW):
            idx = (king_holder_idx - offset) % PLAYER_COUNT
            self.players[idx].role = role
        self._roles_assigned = True

    def _find_king_of_spades(self) -> int:
        """Return the player index holding the King of Spades."""
        for i, player in enumerate(self.players):
            for card in player.hand:
                if card.is_king_of_spades:
                    return i
        return random.randint(0, PLAYER_COUNT - 1)

    def _set_attack_defense_from_roles(self) -> None:
        """Set initial attacker (Servant) and defender (Queen) indices."""
        role_to_idx = {p.role: i for i, p in enumerate(self.players)}
        self.attacker_idx = role_to_idx[ROLE_SERVANT]
        self.defender_idx = role_to_idx[ROLE_QUEEN]

    def set_attacker_defender(self, attacker_id: int, defender_id: int) -> None:
        """Point attacker/defender indices at the given players."""
        for i, p in enumerate(self.players):
            if p.player_id == attacker_id:
                self.attacker_idx = i
            if p.player_id == defender_id:
                self.defender_idx = i

    def declare_trump(self, suit: str) -> bool:
        """King declares the trump suit."""
        if suit not in SUITS:
            return False
        self.trump_suit = suit
        return True

    def end_round(self) -> None:
        """Advance the round counter and clear the table."""
        self.round_number += 1
        self._clear_table()

    def _clear_table(self) -> None:
        """Remove all cards from the table."""
        self.table_attack.clear()
        self.table_defense.clear()

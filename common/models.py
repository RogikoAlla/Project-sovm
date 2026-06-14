"""Shared data models: Card, PlayerInfo, GameState, build_deck."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import ClassVar, Optional

from common.constants import (
    DECK_36,
    KING_OF_SPADES_RANK,
    KING_OF_SPADES_SUIT,
    RANKS_36,
    SUITS,
    SUIT_SYMBOLS,
)


@dataclass(frozen=True, order=False)
class Card:
    """Immutable playing card identified by rank and suit."""

    rank: str
    suit: str

    _RANK_ORDER_36: ClassVar[tuple] = RANKS_36
    _RANK_ORDER_52: ClassVar[tuple] = ("2", "3", "4", "5") + RANKS_36

    def rank_value(self, deck_size: int = DECK_36) -> int:
        """Return numeric strength of this card's rank (King > Ace in KAS)."""
        order = self._RANK_ORDER_36 if deck_size == DECK_36 else self._RANK_ORDER_52
        base = list(order)
        if "K" in base and "A" in base:
            base.remove("K")
            base.append("K")
        return base.index(self.rank) if self.rank in base else -1

    def beats(self, other: "Card", trump: str, deck_size: int = DECK_36) -> bool:
        """Return True if this card beats *other* under Durak + KAS rules."""
        if self.suit == other.suit:
            return self.rank_value(deck_size) > other.rank_value(deck_size)
        if self.suit == trump and other.suit != trump:
            return True
        return False

    @property
    def symbol(self) -> str:
        """Return Unicode suit symbol for display."""
        return SUIT_SYMBOLS.get(self.suit, self.suit)

    def __str__(self) -> str:
        """Return human-readable card label like ``'A♠'``."""
        return f"{self.rank}{self.symbol}"

    def __repr__(self) -> str:
        """Return developer representation."""
        return f"Card({self.rank!r}, {self.suit!r})"

    def to_dict(self) -> dict:
        """Serialize card to a JSON-compatible dictionary."""
        return {"rank": self.rank, "suit": self.suit}

    @classmethod
    def from_dict(cls, data: dict) -> Card:
        """Deserialize card from a dictionary."""
        return cls(rank=data["rank"], suit=data["suit"])

    @property
    def is_king_of_spades(self) -> bool:
        """Return True if this is the King of Spades (role-determining card)."""
        return self.rank == KING_OF_SPADES_RANK and self.suit == KING_OF_SPADES_SUIT


def build_deck(deck_size: int = DECK_36) -> list[Card]:
    """Build and return a shuffled deck of the given size."""
    ranks = RANKS_36 if deck_size == DECK_36 else ("2", "3", "4", "5") + RANKS_36
    cards = [Card(rank=r, suit=s) for s in SUITS for r in ranks]
    random.shuffle(cards)
    return cards


@dataclass
class PlayerInfo:
    """Lightweight player descriptor shared between client and server."""

    player_id: int
    name: str
    role: Optional[str] = None
    hand_size: int = 0
    is_active: bool = True

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PlayerInfo:
        """Deserialize from dict."""
        return cls(**data)


@dataclass
class GameState:
    """Full game state snapshot sent to each client."""

    players: list[PlayerInfo]
    your_hand: list[Card]
    trump_suit: str
    deck_size: int
    table_attack: list[Card] = field(default_factory=list)
    table_defense: dict = field(default_factory=dict)
    current_attacker_id: int = -1
    current_defender_id: int = -1
    king_swap_used: bool = False
    round_number: int = 1
    message: str = ""

    def to_dict(self) -> dict:
        """Serialize full game state to JSON-compatible dict."""
        return {
            "players": [p.to_dict() for p in self.players],
            "your_hand": [c.to_dict() for c in self.your_hand],
            "trump_suit": self.trump_suit,
            "deck_size": self.deck_size,
            "table_attack": [c.to_dict() for c in self.table_attack],
            "table_defense": {k: v.to_dict() for k, v in self.table_defense.items()},
            "current_attacker_id": self.current_attacker_id,
            "current_defender_id": self.current_defender_id,
            "king_swap_used": self.king_swap_used,
            "round_number": self.round_number,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GameState:
        """Deserialize from dict."""
        return cls(
            players=[PlayerInfo.from_dict(p) for p in data["players"]],
            your_hand=[Card.from_dict(c) for c in data["your_hand"]],
            trump_suit=data["trump_suit"],
            deck_size=data["deck_size"],
            table_attack=[Card.from_dict(c) for c in data["table_attack"]],
            table_defense={
                k: Card.from_dict(v) for k, v in data.get("table_defense", {}).items()
            },
            current_attacker_id=data.get("current_attacker_id", -1),
            current_defender_id=data.get("current_defender_id", -1),
            king_swap_used=data.get("king_swap_used", False),
            round_number=data.get("round_number", 1),
            message=data.get("message", ""),
        )

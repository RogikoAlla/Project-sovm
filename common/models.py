"""Shared data models: Card."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from common.constants import (
    DECK_36,
    KING_OF_SPADES_RANK,
    KING_OF_SPADES_SUIT,
    RANKS_36,
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

"""Shared data models: Card."""

from __future__ import annotations

from dataclasses import dataclass

from common.constants import SUIT_SYMBOLS


@dataclass(frozen=True, order=False)
class Card:
    """Immutable playing card identified by rank and suit."""

    rank: str
    suit: str

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

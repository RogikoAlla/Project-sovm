"""Unit tests for common.models: Card."""

import pytest

from common.models import Card


class TestCard:
    """Tests for the Card dataclass."""

    def test_str_spades(self):
        """Card __str__ should include rank and suit symbol."""
        card = Card("A", "spades")
        assert str(card) == "A\u2660"

    def test_str_hearts(self):
        """Red suit card should use heart symbol."""
        card = Card("K", "hearts")
        assert str(card) == "K\u2665"

    def test_to_dict_roundtrip(self):
        """Card serialization and deserialization should be lossless."""
        card = Card("10", "diamonds")
        assert Card.from_dict(card.to_dict()) == card

    def test_card_frozen(self):
        """Card should be immutable (frozen dataclass)."""
        card = Card("7", "clubs")
        with pytest.raises(Exception):
            card.rank = "8"  # type: ignore

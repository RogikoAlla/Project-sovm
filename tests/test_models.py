"""Unit tests for common.models: Card."""

import pytest

from common.constants import DECK_36
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

    def test_rank_value_king_beats_ace_36(self):
        """In KAS, King beats Ace — King rank value should be higher."""
        king = Card("K", "spades")
        ace = Card("A", "spades")
        assert king.rank_value(DECK_36) > ace.rank_value(DECK_36)

    def test_beats_same_suit_higher_wins(self):
        """Higher card of same suit should beat lower card."""
        high = Card("A", "spades")
        low = Card("6", "spades")
        assert high.beats(low, "hearts")

    def test_beats_trump_beats_non_trump(self):
        """Any trump card beats any non-trump card."""
        trump_card = Card("6", "hearts")
        plain_card = Card("A", "spades")
        assert trump_card.beats(plain_card, "hearts")

    def test_non_trump_cannot_beat_trump(self):
        """Non-trump card should not beat a trump card."""
        plain = Card("A", "spades")
        trump_card = Card("6", "hearts")
        assert not plain.beats(trump_card, "hearts")

    def test_king_of_spades_detection(self):
        """is_king_of_spades should identify the correct card."""
        assert Card("K", "spades").is_king_of_spades
        assert not Card("A", "spades").is_king_of_spades
        assert not Card("K", "hearts").is_king_of_spades

    def test_to_dict_roundtrip(self):
        """Card serialization and deserialization should be lossless."""
        card = Card("10", "diamonds")
        assert Card.from_dict(card.to_dict()) == card

    def test_card_frozen(self):
        """Card should be immutable (frozen dataclass)."""
        card = Card("7", "clubs")
        with pytest.raises(Exception):
            card.rank = "8"  # type: ignore

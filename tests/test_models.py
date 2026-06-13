"""Unit tests for common.models: Card, build_deck, PlayerInfo, GameState."""

import pytest

from common.constants import DECK_36, DECK_52, SUITS
from common.models import Card, GameState, PlayerInfo, build_deck


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


class TestBuildDeck:
    """Tests for the deck builder."""

    def test_deck_36_length(self):
        """36-card deck should contain exactly 36 cards."""
        assert len(build_deck(DECK_36)) == 36

    def test_deck_52_length(self):
        """52-card deck should contain exactly 52 cards."""
        assert len(build_deck(DECK_52)) == 52

    def test_deck_unique_cards(self):
        """All cards in the deck should be unique."""
        deck = build_deck(DECK_36)
        assert len(set(deck)) == len(deck)

    def test_deck_contains_king_of_spades(self):
        """Deck should always contain the King of Spades."""
        deck = build_deck(DECK_36)
        assert any(c.is_king_of_spades for c in deck)

    def test_deck_all_suits_represented(self):
        """All four suits should appear in the deck."""
        deck = build_deck(DECK_36)
        assert {c.suit for c in deck} == set(SUITS)


class TestPlayerInfo:
    """Tests for PlayerInfo serialization."""

    def test_roundtrip(self):
        """PlayerInfo should serialize and deserialize without data loss."""
        p = PlayerInfo(player_id=2, name="Alice", role="King", hand_size=9, is_active=True)
        assert PlayerInfo.from_dict(p.to_dict()) == p

    def test_defaults(self):
        """PlayerInfo defaults should reflect inactive/unassigned state."""
        p = PlayerInfo(player_id=0, name="Bob")
        assert p.role is None
        assert p.hand_size == 0


class TestGameState:
    """Tests for GameState serialization."""

    def _sample_state(self):
        """Return a minimal valid GameState."""
        players = [
            PlayerInfo(i, f"P{i}", role=r)
            for i, r in enumerate(["King", "Ace", "Queen", "Servant"])
        ]
        return GameState(
            players=players,
            your_hand=[Card("A", "spades"), Card("6", "hearts")],
            trump_suit="hearts",
            deck_size=36,
        )

    def test_roundtrip(self):
        """GameState to_dict/from_dict roundtrip should preserve all fields."""
        state = self._sample_state()
        restored = GameState.from_dict(state.to_dict())
        assert restored.trump_suit == state.trump_suit
        assert len(restored.your_hand) == len(state.your_hand)
        assert len(restored.players) == len(state.players)

    def test_table_cards_serialized(self):
        """Table attack and defense cards should survive serialization."""
        state = self._sample_state()
        state.table_attack = [Card("K", "clubs")]
        state.table_defense = {"0": Card("A", "clubs")}
        restored = GameState.from_dict(state.to_dict())
        assert len(restored.table_attack) == 1
        assert "0" in restored.table_defense

"""Unit tests for server.game_engine.GameEngine."""

import pytest

from common.constants import DECK_36, ROLE_ACE, ROLE_KING, ROLE_QUEEN, ROLE_SERVANT
from common.models import Card
from server.game_engine import GameEngine, ServerPlayer


def _make_players():
    """Create four named ServerPlayer instances."""
    return [ServerPlayer(player_id=i, name=f"P{i}") for i in range(4)]


def _make_engine():
    """Create and deal an engine with four players."""
    players = _make_players()
    engine = GameEngine(players, DECK_36)
    engine.deal()
    return engine


class TestGameEngineDeal:
    """Tests for initial deal and role assignment."""

    def test_each_player_gets_9_cards(self):
        """After dealing, each player should hold exactly 9 cards."""
        engine = _make_engine()
        for p in engine.players:
            assert len(p.hand) == 9

    def test_all_roles_assigned(self):
        """All four roles should be assigned after deal."""
        engine = _make_engine()
        roles = {p.role for p in engine.players}
        assert roles == {ROLE_KING, ROLE_ACE, ROLE_QUEEN, ROLE_SERVANT}

    def test_no_duplicate_cards(self):
        """All cards across all hands should be unique."""
        engine = _make_engine()
        all_cards = [c for p in engine.players for c in p.hand]
        assert len(set(all_cards)) == len(all_cards)

    def test_roles_not_reassigned_on_redeal(self):
        """Roles from previous round should persist through redeal."""
        engine = _make_engine()
        roles_before = {p.player_id: p.role for p in engine.players}
        engine.end_round()
        engine.deal()
        roles_after = {p.player_id: p.role for p in engine.players}
        assert roles_before == roles_after


class TestTrumpDeclaration:
    """Tests for trump suit declaration."""

    def test_valid_suit_accepted(self):
        """Declaring a valid suit should return True."""
        engine = _make_engine()
        assert engine.declare_trump("hearts") is True
        assert engine.trump_suit == "hearts"

    def test_invalid_suit_rejected(self):
        """Declaring an unknown suit should return False."""
        engine = _make_engine()
        assert engine.declare_trump("bananas") is False


class TestAttackDefense:
    """Tests for attack card plays."""

    def _setup_attack(self):
        """Set up engine with known hands for attack testing."""
        engine = _make_engine()
        engine.declare_trump("spades")
        engine.attacker_idx = 0
        engine.defender_idx = 1
        return engine

    def test_valid_attack(self):
        """Attacker should be able to play any card from their hand."""
        engine = self._setup_attack()
        attacker = engine.players[0]
        card = attacker.hand[0]
        ok, err = engine.play_attack_card(attacker.player_id, card)
        assert ok, err
        assert card in engine.table_attack
        assert card not in attacker.hand

    def test_wrong_player_attack_fails(self):
        """Non-attacker player should not be able to attack."""
        engine = self._setup_attack()
        non_attacker = engine.players[1]
        card = non_attacker.hand[0]
        ok, err = engine.play_attack_card(non_attacker.player_id, card)
        assert not ok

    def test_card_not_in_hand_fails(self):
        """Playing a card not in hand should fail."""
        engine = self._setup_attack()
        attacker = engine.players[0]
        fake = Card("A", "diamonds")
        if fake in attacker.hand:
            pytest.skip("Card happens to be in hand")
        ok, err = engine.play_attack_card(attacker.player_id, fake)
        assert not ok

    def test_valid_defense(self):
        """Defender should be able to beat an attack card with a stronger same-suit card."""
        engine = self._setup_attack()
        attacker = engine.players[0]
        defender = engine.players[1]
        for atk_card in attacker.hand:
            for def_card in defender.hand:
                if def_card.beats(atk_card, engine.trump_suit, DECK_36):
                    engine.play_attack_card(attacker.player_id, atk_card)
                    ok, err = engine.play_defense_card(defender.player_id, 0, def_card)
                    assert ok, err
                    assert def_card in engine.table_defense.values()
                    return
        pytest.skip("No valid defense pair found in this deal")

    def test_defender_done_clears_table(self):
        """After all cards are defended, defender_done should clear the table."""
        engine = self._setup_attack()
        attacker = engine.players[0]
        defender = engine.players[1]
        for atk_card in attacker.hand:
            for def_card in defender.hand:
                if def_card.beats(atk_card, engine.trump_suit, DECK_36):
                    engine.play_attack_card(attacker.player_id, atk_card)
                    engine.play_defense_card(defender.player_id, 0, def_card)
                    ok, err = engine.defender_done()
                    assert ok, err
                    assert len(engine.table_attack) == 0
                    assert len(engine.table_defense) == 0
                    return
        pytest.skip("No valid defense pair found in this deal")

    def test_defender_done_fails_with_undefended(self):
        """defender_done should fail while attack cards remain undefended."""
        engine = self._setup_attack()
        attacker = engine.players[0]
        engine.play_attack_card(attacker.player_id, attacker.hand[0])
        ok, err = engine.defender_done()
        assert not ok
        assert "отбиты" in err


class TestDefenderTakes:
    """Tests for defender picking up table cards."""

    def test_defender_takes_clears_table(self):
        """After take, table should be empty and defender hand grows."""
        engine = _make_engine()
        engine.attacker_idx = 0
        engine.defender_idx = 1
        attacker = engine.players[0]
        defender = engine.players[1]
        card = attacker.hand[0]
        engine.play_attack_card(attacker.player_id, card)
        hand_size_before = len(defender.hand)
        ok, err = engine.defender_takes(defender.player_id)
        assert ok, err
        assert len(engine.table_attack) == 0
        assert len(defender.hand) > hand_size_before

    def test_defender_takes_swaps_roles(self):
        """Attacker and defender should swap roles after take (default case)."""
        engine = _make_engine()
        engine.attacker_idx = 0
        engine.defender_idx = 1
        attacker = engine.players[0]
        defender = engine.players[1]
        attacker.role = ROLE_SERVANT
        defender.role = ROLE_QUEEN
        engine.play_attack_card(attacker.player_id, attacker.hand[0])
        engine.defender_takes(defender.player_id)
        assert attacker.role == ROLE_QUEEN
        assert defender.role == ROLE_SERVANT

    def test_servant_takes_from_king_no_swap(self):
        """Servant taking from King should NOT swap roles."""
        engine = _make_engine()
        engine.attacker_idx = 0
        engine.defender_idx = 1
        attacker = engine.players[0]
        defender = engine.players[1]
        attacker.role = ROLE_KING
        defender.role = ROLE_SERVANT
        engine.play_attack_card(attacker.player_id, attacker.hand[0])
        engine.defender_takes(defender.player_id)
        assert attacker.role == ROLE_KING
        assert defender.role == ROLE_SERVANT


class TestKingBlindSwap:
    """Tests for King's blind swap privilege."""

    def test_swap_once(self):
        """King should be able to swap once and flag should be set."""
        engine = _make_engine()
        king = next(p for p in engine.players if p.role == ROLE_KING)
        other = next(p for p in engine.players if p.role != ROLE_KING)
        king_hand_before = list(king.hand)
        other_hand_before = list(other.hand)
        ok, err = engine.king_blind_swap(king.player_id, other.player_id)
        assert ok, err
        assert engine.king_swap_used is True
        assert king.hand == other_hand_before
        assert other.hand == king_hand_before

    def test_swap_twice_fails(self):
        """Second swap attempt should fail."""
        engine = _make_engine()
        king = next(p for p in engine.players if p.role == ROLE_KING)
        other = next(p for p in engine.players if p.role != ROLE_KING)
        engine.king_blind_swap(king.player_id, other.player_id)
        ok, _ = engine.king_blind_swap(king.player_id, other.player_id)
        assert not ok

    def test_non_king_cannot_swap(self):
        """Non-King player should not be able to initiate swap."""
        engine = _make_engine()
        servant = next(p for p in engine.players if p.role == ROLE_SERVANT)
        other = next(p for p in engine.players if p.player_id != servant.player_id)
        ok, _ = engine.king_blind_swap(servant.player_id, other.player_id)
        assert not ok


class TestBuildGameState:
    """Tests for game state snapshot building."""

    def test_hand_visible_to_owner(self):
        """Player should see their own hand in their snapshot."""
        engine = _make_engine()
        pid = engine.players[0].player_id
        state = engine.build_game_state(pid)
        assert len(state.your_hand) == len(engine.players[0].hand)

    def test_players_included(self):
        """All four players should appear in the snapshot."""
        engine = _make_engine()
        state = engine.build_game_state(engine.players[0].player_id)
        assert len(state.players) == 4

    def test_table_and_turn_fields(self):
        """Snapshot should include table cards and current turn ids."""
        engine = _make_engine()
        engine.declare_trump("hearts")
        engine.attacker_idx = 0
        engine.defender_idx = 1
        card = engine.players[0].hand[0]
        engine.play_attack_card(engine.players[0].player_id, card)
        state = engine.build_game_state(engine.players[0].player_id)
        assert len(state.table_attack) == 1
        assert state.trump_suit == "hearts"
        assert state.current_attacker_id == 0
        assert state.current_defender_id == 1


class TestRoundLifecycle:
    """Tests for round completion detection."""

    def test_is_round_over_when_one_active(self):
        """Round ends when at most one player remains active."""
        engine = _make_engine()
        for p in engine.players[1:]:
            p.hand.clear()
            p.is_active = False
        assert engine.is_round_over() is True

    def test_is_round_over_false_with_multiple_active(self):
        """Round continues while multiple players hold cards."""
        engine = _make_engine()
        assert engine.is_round_over() is False

    def test_end_round_increments_counter(self):
        """end_round should advance round_number and clear the table."""
        engine = _make_engine()
        engine.table_attack.append(engine.players[0].hand[0])
        engine.end_round()
        assert engine.round_number == 2
        assert len(engine.table_attack) == 0

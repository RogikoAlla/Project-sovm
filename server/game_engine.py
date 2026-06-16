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
    ROLE_KING,
    ROLE_QUEEN,
    ROLE_SERVANT,
    ROLES_CCW,
    SUITS,
)
from common.models import Card, PlayerInfo, build_deck

MAX_TABLE_CARDS = 6


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

    def table_ranks(self) -> set:
        """Return ranks currently on the table (attack + defense)."""
        ranks = {c.rank for c in self.table_attack}
        ranks |= {c.rank for c in self.table_defense.values()}
        return ranks

    def undefended_indices(self) -> list[int]:
        """Return indices of attack cards not yet beaten."""
        return [i for i in range(len(self.table_attack)) if i not in self.table_defense]

    def validate_attack_batch(self, player_id: int, cards: list[Card]) -> tuple[bool, str]:
        """Validate attack cards per Durak rules without applying them."""
        if not cards:
            return False, "Не выбрано ни одной карты"
        player = self._get_player(player_id)
        if player is None:
            return False, "Игрок не найден"
        if self.players[self.attacker_idx].player_id != player_id:
            return False, "Сейчас не ваш ход атаки"

        seen: list[Card] = []
        for c in cards:
            if c in seen:
                return False, "Нельзя указывать одну карту дважды"
            seen.append(c)
        for c in cards:
            if c not in player.hand:
                return False, f"Карты {c} нет в вашей руке"

        defender = self.players[self.defender_idx]
        if not self.table_attack:
            if len({c.rank for c in cards}) > 1:
                return False, "Первая атака: все карты должны быть одного ранга"
        else:
            allowed = self.table_ranks()
            for c in cards:
                if c.rank not in allowed:
                    return False, f"Нельзя подкинуть {c}: ранга «{c.rank}» нет на столе"

        if len(self.table_attack) + len(cards) > MAX_TABLE_CARDS:
            return False, f"Максимум {MAX_TABLE_CARDS} карт в атаке"
        undefended = len(self.table_attack) - len(self.table_defense)
        if undefended + len(cards) > len(defender.hand):
            return False, "У защитника не хватит карт, чтобы отбиться"
        return True, ""

    def apply_attack_batch(self, player_id: int, cards: list[Card]) -> tuple[bool, str]:
        """Validate and place attack cards on the table."""
        ok, err = self.validate_attack_batch(player_id, cards)
        if not ok:
            return False, err
        player = self._get_player(player_id)
        assert player is not None
        for c in cards:
            player.remove_card(c)
            self.table_attack.append(c)
        return True, ""

    def play_attack_card(self, player_id: int, card: Card) -> tuple[bool, str]:
        """Place a single attacking card (convenience wrapper)."""
        return self.apply_attack_batch(player_id, [card])

    def play_defense_card(self, player_id: int, attack_idx: int, card: Card) -> tuple[bool, str]:
        """Beat one attack card with a defending card."""
        player = self._get_player(player_id)
        if player is None:
            return False, "Игрок не найден"
        defender = self.players[self.defender_idx]
        if defender.player_id != player_id:
            return False, "Сейчас не ваша защита"
        if attack_idx < 0 or attack_idx >= len(self.table_attack):
            return False, "Неверный номер карты на столе"
        if attack_idx in self.table_defense:
            return False, "Эта карта уже отбита"
        if card not in player.hand:
            return False, f"Карты {card} нет в вашей руке"
        attack_card = self.table_attack[attack_idx]
        if not card.beats(attack_card, self.trump_suit, self.deck_size):
            return False, f"{card} не бьёт {attack_card}"
        player.remove_card(card)
        self.table_defense[attack_idx] = card
        return True, ""

    def defender_takes(self, player_id: int) -> tuple[bool, str]:
        """Defender picks up all table cards; attacker and defender swap roles."""
        defender = self.players[self.defender_idx]
        if defender.player_id != player_id:
            return False, "Забрать карты может только защищающийся"
        picked = list(self.table_attack) + list(self.table_defense.values())
        defender.hand.extend(picked)
        attacker = self.players[self.attacker_idx]
        if not (defender.role == ROLE_SERVANT and attacker.role == ROLE_KING):
            attacker.role, defender.role = defender.role, attacker.role
        self._clear_table()
        self._check_active_status()
        return True, ""

    def defender_done(self) -> tuple[bool, str]:
        """Declare a beat when all attack cards are defended."""
        if self.undefended_indices():
            return False, "Ещё не все карты отбиты"
        self._clear_table()
        self._check_active_status()
        return True, ""

    def end_round(self) -> None:
        """Advance the round counter and clear the table."""
        self.round_number += 1
        self._clear_table()

    def _clear_table(self) -> None:
        """Remove all cards from the table."""
        self.table_attack.clear()
        self.table_defense.clear()

    def _get_player(self, player_id: int) -> Optional[ServerPlayer]:
        """Look up a player by ID."""
        for p in self.players:
            if p.player_id == player_id:
                return p
        return None

    def _check_active_status(self) -> None:
        """Mark players with empty hands as inactive."""
        for player in self.players:
            if not player.hand:
                player.is_active = False

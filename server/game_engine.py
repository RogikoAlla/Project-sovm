"""Core game engine: state machine for King and Servant rounds.

Attack/defense rules follow classic Durak, with one twist from KAS: the King
(rank) beats the Ace (rank). Only the attacker may add cards (подкидывание) or
declare a beat. Added cards must match a rank already present on the table.

This module is pure game logic — no network or UI dependencies.
"""

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
from common.models import Card, GameState, PlayerInfo, build_deck

MAX_TABLE_CARDS = 6  # standard Durak limit per attack


@dataclass
class ServerPlayer:
    """Server-side player state including the private hand.

    Args:
        player_id: Unique integer ID.
        name: Display name.
        role: Current role or ``None`` before the first deal.
        hand: Private list of cards (never sent to other clients).
        is_active: ``True`` while the player still has cards this round.
    """

    player_id: int
    name: str
    role: Optional[str] = None
    hand: list[Card] = field(default_factory=list)
    is_active: bool = True

    def to_info(self) -> PlayerInfo:
        """Return a public-facing ``PlayerInfo`` (hand hidden as a count)."""
        return PlayerInfo(
            player_id=self.player_id,
            name=self.name,
            role=self.role,
            hand_size=len(self.hand),
            is_active=self.is_active,
        )

    def remove_card(self, card: Card) -> bool:
        """Remove *card* from hand if present.

        Returns:
            ``True`` if the card was found and removed.
        """
        try:
            self.hand.remove(card)
            return True
        except ValueError:
            return False


class GameEngine:
    """Manages a complete multi-round King and Servant session.

    Handles dealing, role assignment (via King of Spades), trump declaration,
    Durak-style attack/defence with подкидывание, role swaps on take, and the
    King's one-time blind hand swap per round.

    Args:
        players: Ordered list of four ``ServerPlayer`` objects.
        deck_size: 36 or 52.
    """

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
        """Shuffle and deal cards; assign roles based on the King of Spades.

        Resets trump, blind-swap flag, and table. Roles are assigned only on
        the first deal of the session; subsequent deals keep existing roles.
        """
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
        """Point attacker/defender indices at the given players.

        Called by the server before each exchange to keep turn order in sync.
        """
        for i, p in enumerate(self.players):
            if p.player_id == attacker_id:
                self.attacker_idx = i
            if p.player_id == defender_id:
                self.defender_idx = i

    def declare_trump(self, suit: str) -> bool:
        """King declares the trump suit.

        Args:
            suit: Suit name to set as trump.

        Returns:
            ``True`` if the suit is valid and was set.
        """
        if suit not in SUITS:
            return False
        self.trump_suit = suit
        return True

    def table_ranks(self) -> set:
        """Return ranks currently on the table (attack + defence cards)."""
        ranks = {c.rank for c in self.table_attack}
        ranks |= {c.rank for c in self.table_defense.values()}
        return ranks

    def undefended_indices(self) -> list[int]:
        """Return indices of attack cards not yet beaten."""
        return [i for i in range(len(self.table_attack)) if i not in self.table_defense]

    def validate_attack_batch(self, player_id: int, cards: list[Card]) -> tuple[bool, str]:
        """Validate attack cards per Durak rules without applying them.

        Returns:
            ``(ok, error_message)`` — empty message on success.
        """
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
        """Beat one attack card with a defending card.

        Args:
            player_id: ID of the defending player.
            attack_idx: Index in ``table_attack`` being defended.
            card: Card used to defend (must beat per Durak; King > Ace).

        Returns:
            ``(ok, error_message)``.
        """
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
        """Defender picks up all table cards; attacker and defender swap roles.

        Exception: Servant taking from King does **not** swap roles.
        """
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
        """Declare a beat when all attack cards are defended; clear the table."""
        if self.undefended_indices():
            return False, "Ещё не все карты отбиты"
        self._clear_table()
        self._check_active_status()
        return True, ""

    def king_blind_swap(self, king_player_id: int, target_player_id: int) -> tuple[bool, str]:
        """King swaps hands blindly with another player (once per round)."""
        if self.king_swap_used:
            return False, "Обмен уже использован"
        king = self._get_player(king_player_id)
        target = self._get_player(target_player_id)
        if king is None or target is None:
            return False, "Неверный игрок"
        if king.role != ROLE_KING:
            return False, "Обмен доступен только Королю"
        if king_player_id == target_player_id:
            return False, "Король не может меняться сам с собой"
        king.hand, target.hand = target.hand, king.hand
        self.king_swap_used = True
        return True, ""

    def is_round_over(self) -> bool:
        """Return True if at most one active player still holds cards."""
        return len([p for p in self.players if p.is_active]) <= 1

    def build_game_state(self, for_player_id: int) -> GameState:
        """Build a ``GameState`` snapshot tailored for *for_player_id*.

        The receiving player's private hand is included; ``table_defense`` keys
        are string indices for the wire protocol.
        """
        target = self._get_player(for_player_id)
        hand = target.hand if target else []
        attacker = self.players[self.attacker_idx]
        defender = self.players[self.defender_idx]
        return GameState(
            players=[p.to_info() for p in self.players],
            your_hand=hand,
            trump_suit=self.trump_suit,
            deck_size=self.deck_size,
            table_attack=list(self.table_attack),
            table_defense={str(k): v for k, v in self.table_defense.items()},
            current_attacker_id=attacker.player_id,
            current_defender_id=defender.player_id,
            king_swap_used=self.king_swap_used,
            round_number=self.round_number,
        )

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
        """Mark players with empty hands as inactive (role is preserved)."""
        for player in self.players:
            if not player.hand:
                player.is_active = False

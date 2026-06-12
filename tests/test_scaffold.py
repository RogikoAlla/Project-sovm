"""Smoke tests for project scaffold."""

import common.constants as const


def test_game_constants_defined():
    assert const.PLAYER_COUNT == 4
    assert const.DECK_36 == 36
    assert len(const.ROLES_CCW) == 4

import pytest
from hll_rcon.response_types import Player, PlayerInfo, PlayerScore
from hll_rcon.types import Team
from loguru import logger

from hll_game_monitor.pollers.player_state import (
    PlayerStateChange,
    get_player_state_change,
)


def mock_player_info(
    player_name="Some Name",
    player_id="123456789012345678",
    team=Team.ALLIES.value,
    role="Rifleman",
    loadout=None,
    unit=None,
    score: PlayerScore | None = None,
    level=1,
):
    if score is None:
        score = PlayerScore()

    return PlayerInfo(
        player_name=player_name,
        player_id=player_id,
        team=team,
        role=role,
        loadout=loadout,
        unit=unit,
        score=score,
        level=level,
    )


def test_get_player_state_change_team():
    old_state = mock_player_info(team=Team.ALLIES.value)
    new_state = mock_player_info(team=Team.AXIS.value)

    change = get_player_state_change(old_state=old_state, new_state=new_state)
    assert change == PlayerStateChange(
        level=None,
        team=Team.AXIS.value,
        role=None,
        loadout=None,
        unit=None,
        score_deltas=PlayerScore(),
    )


def test_get_player_state_change_level():
    old_state = mock_player_info(level=1)
    new_state = mock_player_info(level=2)

    change = get_player_state_change(old_state=old_state, new_state=new_state)
    assert change == PlayerStateChange(
        level=2,
        team=None,
        role=None,
        loadout=None,
        unit=None,
        score_deltas=PlayerScore(),
    )

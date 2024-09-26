from datetime import datetime, timedelta, timezone

import pytest
from hll_rcon.response_types import GameState
from loguru import logger

from hll_game_monitor.utils import get_game_state_within_buffer


def test_get_game_state_within_buffer_match_start():
    events: list[GameState] = [
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 32, 48, 885143, tzinfo=timezone.utc),
            allied_players=43,
            axis_players=41,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5378),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 32, 59, 37691, tzinfo=timezone.utc),
            allied_players=43,
            axis_players=42,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5368),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        # Match start!
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 33, 9, 240908, tzinfo=timezone.utc),
            allied_players=43,
            axis_players=39,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5357),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 33, 19, 543452, tzinfo=timezone.utc),
            allied_players=42,
            axis_players=39,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5347),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 33, 29, 706380, tzinfo=timezone.utc),
            allied_players=41,
            axis_players=41,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5337),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
    ]

    # datetime(2024, 9, 25, 21, 32, 59, 37691, tzinfo=timezone.utc)
    # match start
    # datetime(2024, 9, 25, 21, 33, 9, 240908, tzinfo=timezone.utc)

    res = get_game_state_within_buffer(
        match_start=True,
        event_timestamp=datetime(2024, 9, 25, 21, 33, 3, 0, tzinfo=timezone.utc),
        events=events,
        buffer_secs=15,
    )

    assert res and res.timestamp == datetime(
        2024, 9, 25, 21, 33, 9, 240908, tzinfo=timezone.utc
    )

    logger.info(f"{res=}")
    # assert False


def test_get_game_state_within_buffer_match_end():
    events: list[GameState] = [
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 32, 48, 885143, tzinfo=timezone.utc),
            allied_players=43,
            axis_players=41,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5378),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 32, 59, 37691, tzinfo=timezone.utc),
            allied_players=43,
            axis_players=42,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5368),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        # Match end!
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 33, 9, 240908, tzinfo=timezone.utc),
            allied_players=43,
            axis_players=39,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5357),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 33, 19, 543452, tzinfo=timezone.utc),
            allied_players=42,
            axis_players=39,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5347),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
        GameState(
            timestamp=datetime(2024, 9, 25, 21, 33, 29, 706380, tzinfo=timezone.utc),
            allied_players=41,
            axis_players=41,
            allied_score=2,
            axis_score=2,
            remaining_time=timedelta(seconds=5337),
            current_map="hill400_warfare",
            next_map="stmereeglise_warfare",
        ),
    ]

    # datetime(2024, 9, 25, 21, 32, 59, 37691, tzinfo=timezone.utc)
    # match end
    # datetime(2024, 9, 25, 21, 33, 9, 240908, tzinfo=timezone.utc)

    gamestate = events[1]

    res = get_game_state_within_buffer(
        match_start=False,
        event_timestamp=datetime(2024, 9, 25, 21, 33, 3, 0, tzinfo=timezone.utc),
        events=events,
        buffer_secs=15,
    )

    logger.info(f"{datetime(2024, 9, 25, 21, 33, 3, 0, tzinfo=timezone.utc)}")
    logger.info(f"{res.timestamp}")

    assert res and res.timestamp == gamestate.timestamp

    logger.info(f"{res=}")
    # assert False

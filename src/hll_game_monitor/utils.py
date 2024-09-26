from datetime import datetime, timedelta, timezone

import pydantic
from hll_rcon.response_types import GameState
from loguru import logger


def get_game_state_within_buffer(
    match_start: bool,
    event_timestamp: pydantic.AwareDatetime,
    events: list[GameState],
    buffer_secs: int = 15,
) -> GameState | None:

    if match_start:
        sorted_events = sorted(events, key=lambda e: e.timestamp, reverse=True)
    else:
        sorted_events = sorted(events, key=lambda e: e.timestamp, reverse=False)

    found_game_state: GameState | None = None

    for gamestate in sorted_events:
        if match_start:
            # we want the first timestamp *after* the match start
            delta = (gamestate.timestamp - event_timestamp).total_seconds()
        else:
            # we want the last timestamp *before* the match start
            delta = (event_timestamp - gamestate.timestamp).total_seconds()

        if delta > 0 and delta < buffer_secs:
            found_game_state = gamestate

    return found_game_state

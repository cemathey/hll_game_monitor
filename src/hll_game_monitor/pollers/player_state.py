import hashlib
import os
from datetime import datetime, timedelta, timezone
from itertools import batched
from pprint import pprint
from typing import Sequence

import orjson
import pydantic
import redis
import trio
from hll_rcon.log_types import (
    BanLog,
    BanLogBan,
    ChatLog,
    ConnectLog,
    DisconnectLog,
    EnteredAdminCamLog,
    ExitedAdminCamLog,
    GameLogType,
    GameServerCredentials,
    KickLog,
    KillLog,
    LogTimeStamp,
    MatchEndLog,
    MatchStartLog,
    MessagedPlayerLog,
    TeamKillLog,
    TeamSwitchLog,
    VoteKickCompletedStatusLog,
    VoteKickExpiredLog,
    VoteKickPlayerVoteLog,
    VoteKickResultsLog,
    VoteKickStartedLog,
)
from hll_rcon.rcon import AsyncRcon
from hll_rcon.response_types import (
    AdminGroup,
    AdminId,
    AutoBalanceState,
    AutoBalanceThreshold,
    AvailableMaps,
    CensoredWord,
    GameState,
    HighPingLimit,
    IdleKickTime,
    InvalidTempBan,
    MapRotation,
    MaxQueueSize,
    NumVipSlots,
    PermanentBan,
    Player,
    PlayerInfo,
    PlayerScore,
    ServerName,
    ServerPlayerSlots,
    Squad,
    TeamSwitchCoolDown,
    TemporaryBan,
    VipId,
    VoteKickState,
    VoteKickThreshold,
)
from loguru import logger

from hll_game_monitor.types import Payload

# TODO: probably need to move this to redis or something in case of crashes
PLAYER_STATE_CACHE: dict[datetime, PlayerInfo] = {}

# TODO: make this unique based off CLI params
KEY = "{game_server_id}:player_state"
KEY = KEY.format(game_server_id=1)


class PlayerStateChange(pydantic.BaseModel):
    # TODO: players can't change names without reconnecting, no need ot track?

    level: int | None = pydantic.Field(default=None)
    team: str | None = pydantic.Field(default=None)
    role: str | None = pydantic.Field(default=None)
    loadout: str | None = pydantic.Field(default=None)
    unit: Squad | None = pydantic.Field(default=None)

    score_deltas: PlayerScore = pydantic.Field(default_factory=PlayerScore)


def get_player_state_change(
    old_state: PlayerInfo, new_state: PlayerInfo
) -> PlayerStateChange:

    level: int | None = None
    team: str | None = None
    role: str | None = None
    loadout: str | None = None
    unit: Squad | None = None
    score_delta = PlayerScore()

    # TODO: level 1 bug?
    if old_state.level != new_state.level:
        level = new_state.level

    if old_state.team != new_state.team:
        team = new_state.team
    if old_state.role != new_state.role:
        role = new_state.role
    if old_state.loadout != new_state.loadout:
        loadout = new_state.loadout
    if old_state.unit != new_state.unit:
        unit = new_state.unit

    # TODO: Test this, need to zero out players state on match start/reconnect?
    if old_state.score != new_state.score:
        score_delta = PlayerScore(
            kills=new_state.score.kills - old_state.score.kills,
            deaths=new_state.score.deaths - old_state.score.deaths,
            combat=new_state.score.combat - old_state.score.combat,
            offensive=new_state.score.offensive - old_state.score.offensive,
            defensive=new_state.score.defensive - old_state.score.defensive,
            support=new_state.score.support - old_state.score.support,
        )

    return PlayerStateChange(
        level=level,
        team=team,
        role=role,
        loadout=loadout,
        unit=unit,
        score_deltas=score_delta,
    )


async def get_batched_playerinfo(
    connection: AsyncRcon, players: Sequence[Player], output: list[PlayerInfo]
):
    for p in players:
        logger.info(f"Getting player info for {p.player_name} {p.player_id}")
        p_info = await connection.get_player_info(player_name=p.player_name)
        if p_info:
            output.append(p_info)
        else:
            logger.info(f"Unable to get player info for {p.player_name}")


async def poll_player_state(
    redis_hook: redis.Redis, host: str, port: str, password: str
):
    logger.info(f"Starting poll_player_state")
    num_connections = 5
    poll_time_secs = 10

    rcon = AsyncRcon(host, port, password)
    await rcon.setup()
    connections = [AsyncRcon(host, port, password) for _ in range(num_connections)]

    async with trio.open_nursery() as nursery:
        for idx, c in enumerate(connections):
            logger.info(f"Opening connection {idx+1}")
            nursery.start_soon(c.setup)

    prev_state: dict[str, PlayerInfo] = {}
    while True:

        player_ids = await rcon.get_player_ids()
        logger.info(f"Polling {len(player_ids)} players info")

        # TODO: move this upstream to hll_rcon
        batched_players = list(batched(player_ids.values(), 100 // num_connections))
        player_info: list[PlayerInfo] = []
        async with trio.open_nursery() as nursery:
            polled_at = datetime.now(tz=timezone.utc)
            for connection, players in zip(connections, batched_players):
                nursery.start_soon(
                    get_batched_playerinfo, connection, players, player_info
                )

        logger.info(f"Polled {len(player_info)} players")
        logger.info(f"{player_info[0]=}")

        for idx, p_info in enumerate(player_info):
            old_state = prev_state.get(p_info.player_id)
            prev_state[p_info.player_id] = p_info

            if old_state == prev_state or old_state is None:
                logger.info(f"No state change for {p_info.player_id}")
                continue

            change = get_player_state_change(old_state=old_state, new_state=p_info)

            custom_id = f"{int(polled_at.timestamp())}-{idx}"
            # TODO: fix this so we aren't serializing/deserializing so much
            payload = Payload(
                type=change.model_json_schema()["title"],
                payload=change.model_dump_json(),
            )
            logger.info(f"Adding to stream: {KEY=} {custom_id=} {payload}")
            redis_hook.xadd(
                name=KEY, fields=orjson.loads(payload.model_dump_json()), id=custom_id
            )

        logger.info(f"Sleeping for {poll_time_secs}")
        await trio.sleep(poll_time_secs)
        # break

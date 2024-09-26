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

# TODO: make this unique based off CLI params
KEY = "{game_server_id}:game_state"
KEY = KEY.format(game_server_id=1)


async def poll_game_state(redis_hook: redis.Redis, host: str, port: str, password: str):
    logger.info(f"Starting poll_game_state")
    poll_time_secs = 10

    rcon = AsyncRcon(host, port, password)
    await rcon.setup()

    while True:
        gamestate = await rcon.get_gamestate()
        gamestate.timestamp

        logger.info(f"{gamestate!r}")
        custom_id = f"{int(gamestate.timestamp.timestamp())}-{0}"
        # TODO: fix this so we aren't serializing/deserializing so much
        payload = Payload(
            type=gamestate.model_json_schema()["title"],
            payload=gamestate.model_dump_json(),
        )
        logger.info(f"Adding to stream: {KEY=} {custom_id=} {payload}")
        redis_hook.xadd(
            name=KEY, fields=orjson.loads(payload.model_dump_json()), id=custom_id
        )

        logger.info(f"Sleeping for {poll_time_secs}")
        await trio.sleep(poll_time_secs)
        # break

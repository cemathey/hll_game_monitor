import hashlib
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pprint import pprint
from typing import Any

import orjson
import redis
import redis.exceptions
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
KEY = "{game_server_id}:logs"
KEY = KEY.format(game_server_id=1)

LOG_CACHE: dict[str, GameLogType] = {}


def bucket_by_timestamp(
    logs: list[GameLogType],
) -> list[tuple[datetime, list[GameLogType]]]:
    """Organize logs by their game server timestamp

    Redis streams must be in sequential order, we use custom keys that are the
    unix timestamp of the time the log occurred on the game server, but each
    timestamp can have multiple logs.

    Return each unique timestamp and the logs that occured at that time
    """
    buckets: dict[datetime, list[GameLogType]] = defaultdict(list)

    ordered_logs: list[tuple[datetime, list[GameLogType]]] = []

    for log in logs:
        timestamp = log.time.absolute_timestamp
        buckets[timestamp].append(log)

    for timestamp in buckets.keys():
        ordered_logs.append((timestamp, buckets[timestamp]))

    return ordered_logs


async def poll_logs(redis_hook: redis.Redis, host: str, port: str, password: str):
    logger.info(f"Starting poll_logs")

    startup_mins = 5
    poll_mins = 1
    poll_freq_secs = 10
    log_mins_to_fetch = startup_mins

    rcon = AsyncRcon(host, port, password)
    await rcon.setup()

    # TODO: handle stream errors when adding already seen logs
    first_loop = True
    while True:
        # for match/start end logs we don't get a real map ID, we get bullshit names that can't be uniquely
        # identified in all cases
        # if we poll game state, then we should always (except for first time start up for a game server running a current match)
        # be able to uniquely identify the maps in match/start end logs
        # need to utilize the game_state stream and either find the first game state command *after* a map started for match starts
        # and find the first game state command *before* a map ended for match ends
        # this can be cleaned up later manually, or if the info is unavailable

        if first_loop:
            logs = await rcon.get_game_logs(minutes=log_mins_to_fetch)
            log_mins_to_fetch = poll_mins
            first_loop = False
        else:
            logs = await rcon.get_game_logs(minutes=log_mins_to_fetch)

        logger.info(f"Fetched {len(logs)} logs since {log_mins_to_fetch} minutes ago")
        logs_by_timestamp = bucket_by_timestamp(logs=logs)

        last_seen_id: str | None = None
        try:
            info: dict[str, Any] = redis_hook.xinfo_stream(name=KEY)  # type: ignore
            last_seen_id = info["last-generated-id"].decode()
        except redis.exceptions.ResponseError:
            pass

        for _, bucket in logs_by_timestamp:
            for log in bucket:
                # TODO: we're still occasionally getting errors when adding because of older IDs leaking through somehow
                if last_seen_id and log.id < last_seen_id:
                    continue

                seen = LOG_CACHE.get(log.id)

                if not seen:
                    # TODO: fix this so we aren't serializing/deserializing so much
                    payload = Payload(
                        type=log.model_json_schema()["title"],
                        payload=log.model_dump_json(),
                    )
                    logger.info(f"Adding to stream: {KEY=} {log.id=} {payload}")
                    redis_hook.xadd(
                        name=KEY,
                        fields=orjson.loads(payload.model_dump_json()),
                        id=log.id,
                    )
                    LOG_CACHE[log.id] = log

        logger.info(f"sleeping for {poll_freq_secs}")
        await trio.sleep(poll_freq_secs)
        # break

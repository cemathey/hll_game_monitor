import hashlib
import os
import sys
from pprint import pprint

# import asyncclick as click
import click
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

from hll_game_monitor.pollers.game_state import poll_game_state
from hll_game_monitor.pollers.logs import poll_logs
from hll_game_monitor.pollers.player_state import poll_player_state

logger.remove()
logger.add(sys.stderr, level="INFO")

LOG_CACHE: dict[str, GameLogType] = {}


@click.group()
def cli():
    pass


# TODO: fix typing on ports
@cli.command()
@click.option("-h", "--host", required=True)
@click.option("-p", "--port", required=True, type=click.STRING)
@click.option("-P", "--password", required=True)
def player_state(host: str, port: str, password: str):
    redis_hook = redis.Redis()
    trio.run(poll_player_state, redis_hook, host, port, password)


@cli.command()
@click.option("-h", "--host", required=True)
@click.option("-p", "--port", required=True, type=click.STRING)
@click.option("-P", "--password", required=True)
def game_state(host: str, port: str, password: str):
    redis_hook = redis.Redis()
    trio.run(poll_game_state, redis_hook, host, port, password)


@cli.command()
@click.option("-h", "--host", required=True)
@click.option("-p", "--port", required=True, type=click.STRING)
@click.option("-P", "--password", required=True)
def logs(host: str, port: str, password: str):
    redis_hook = redis.Redis()
    trio.run(poll_logs, redis_hook, host, port, password)


if __name__ == "__main__":
    cli()

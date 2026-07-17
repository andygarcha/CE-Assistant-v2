import logging
import os
from typing import Literal

import aiohttp
import discord

logger = logging.getLogger(__name__)

# main.py sets CE_DEV_MODE=1 (before importing anything that depends on
# IN_CE) when run with `--dev`, to run against the test guild/channels
# instead of the real CE server.
IN_CE = os.environ.get("CE_DEV_MODE") != "1"

CE_CHANNELS = {
    "gameadditions": 949482536726298666,
    "casino": 1080137628604694629,
    "casinolog": 1218980203209035938,
    "privatelog": 1208259110638985246,
    "userlog": 1256832310523859025,
    "proofsubmissions": 747384873320448082,
    "inputlog": 0,
}

CE_CHANNELS["inputlog"] = CE_CHANNELS["privatelog"]  # TODO temp

TEST_CHANNELS = {
    "gameadditions": 1128742486416834570,
    "casino": 811286469251039333,
    "casinolog": 1257381604452466737,
    "privatelog": 1141886539157221457,
    "userlog": 1257381593136365679,
    "proofsubmissions": 1263199416462868522,
    "inputlog": 1294335132236251157,
}

CHANNELS = CE_CHANNELS if IN_CE else TEST_CHANNELS

CHANNEL_NAMES = Literal[
    "gameadditions",
    "casino",
    "casinolog",
    "privatelog",
    "userlog",
    "proofsubmissions",
    "inputlog",
]

GAME_ADDITIONS_ID = CHANNELS["gameadditions"]
CASINO_ID = CHANNELS["casino"]
CASINO_LOG_ID = CHANNELS["casinolog"]
PRIVATE_LOG_ID = CHANNELS["privatelog"]
USER_LOG_ID = CHANNELS["userlog"]
PROOF_SUBMISSIONS_ID = CHANNELS["proofsubmissions"]
INPUT_LOG_ID = CHANNELS["inputlog"]


def id_num(channel_name: CHANNEL_NAMES):
    """
    Returns the channel ID for a given key.
    """
    return CHANNELS.get(channel_name, 0)


def get_channel(client: discord.Client | None, channel: CHANNEL_NAMES):
    # param check
    if client is None or channel not in CHANNELS:
        return None

    # null check
    _channel = client.get_channel(id_num(channel))
    if _channel is None:
        return None

    if isinstance(
        _channel,
        discord.ForumChannel | discord.CategoryChannel | discord.abc.PrivateChannel,
    ):
        return None

    if not hasattr(_channel, "send"):
        logger.error("Channel of type %s has no attribute send.", type(_channel))
        raise Exception

    return _channel


async def send_message(
    client: discord.Client | None,
    channel: CHANNEL_NAMES,
    message: str = "",
    allowed_mentions: bool | list[int] = True,
    embed: discord.Embed | None = None,
) -> bool:
    "Sends a message to a specified channel."
    _channel = get_channel(client, channel)
    if _channel is None:
        return False

    if isinstance(allowed_mentions, list):
        # ping only the specific users in this list (e.g. co-op rolls where
        # each participant has their own ping opt-in), everyone else mentioned
        # in the message text is left unpinged
        mentions = discord.AllowedMentions(
            users=[discord.Object(id=user_id) for user_id in allowed_mentions]
        )
    else:
        mentions = (
            discord.AllowedMentions.all()
            if allowed_mentions
            else discord.AllowedMentions.none()
        )

    if embed is None:
        try:
            await _channel.send(message, allowed_mentions=mentions)
        except (
            aiohttp.ClientConnectionError,
            discord.ConnectionClosed,
            discord.HTTPException,
        ):
            return False
    else:
        try:
            await _channel.send(message, allowed_mentions=mentions, embed=embed)
        except (
            aiohttp.ClientConnectionError,
            discord.ConnectionClosed,
            discord.HTTPException,
        ):
            return False
    return True


async def log_command(
    client: discord.Client,
    interaction: discord.Interaction,
    command_name: str,
    dev_command: bool,
    include_ce_link: bool = True,
    **kwargs,
) -> None:
    """Logs a command to the private log channel.

    Parameters
    ----------
    client : discord.Client
        The bot client.
    interaction : discord.Interaction
        The interaction that triggered the command.
    command_name : str
        The name of the command being run.
    dev_command : bool
        Whether this is a dev command.
    include_ce_link : bool
        Whether to look up the user's CE profile for a linked display name.
    **kwargs
        The parameters of the command, passed as keyword arguments.
    """
    prefix: str = (
        ":white_large_square: dev command" if dev_command else ":blue_square: command"
    )

    display: str
    if include_ce_link:
        from Modules import SupabaseReader

        ce_user = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
        display = (
            ce_user.display_name_with_link
            if ce_user is not None
            else interaction.user.name
        )
    else:
        display = interaction.user.name

    lines = [
        f"{prefix} run by <@{interaction.user.id}> ({display})",
        f"- `/{command_name}`",
    ]
    for k, v in kwargs.items():
        lines.append(f"- {k}={v}")

    await send_message(client, "privatelog", "\n".join(lines), allowed_mentions=False)
    return

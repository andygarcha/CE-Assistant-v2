from typing import Literal
import aiohttp
import discord

IN_CE = True

CE_CHANNELS = {
    "gameadditions" : 949482536726298666,
    "casino" : 1080137628604694629,
    "casinolog" : 1218980203209035938,
    "privatelog" : 1208259110638985246,
    "userlog" : 1256832310523859025,
    "proofsubmissions" : 747384873320448082,
    "inputlog" : 0
}

CE_CHANNELS["inputlog"] = CE_CHANNELS["privatelog"] # TODO temp

TEST_CHANNELS = {
    "gameadditions" : 1128742486416834570,
    "casino" : 811286469251039333,
    "casinolog" : 1257381604452466737,
    "privatelog" : 1141886539157221457,
    "userlog" : 1257381593136365679,
    "proofsubmissions" : 1263199416462868522,
    "inputlog" : 1294335132236251157
}

CHANNELS = CE_CHANNELS if IN_CE else TEST_CHANNELS

CHANNEL_NAMES = Literal[
    "gameadditions",
    "casino",
    "casinolog",
    "privatelog",
    "userlog",
    "proofsubmissions",
    "inputlog"
]

GAME_ADDITIONS_ID = CHANNELS["gameadditions"]
CASINO_ID = CHANNELS["casino"]
CASINO_LOG_ID = CHANNELS["casinolog"]
PRIVATE_LOG_ID = CHANNELS['privatelog']
USER_LOG_ID = CHANNELS["userlog"]
PROOF_SUBMISSIONS_ID = CHANNELS['proofsubmissions']
INPUT_LOG_ID = CHANNELS['inputlog']

def id_num(channel_name : CHANNEL_NAMES) :
    """
    Returns the channel ID for a given key.
    """
    return CHANNELS.get(channel_name, 0)

def get_channel(client: discord.Client | None, channel: CHANNEL_NAMES) -> discord.TextChannel | None:
    # param check
    if client is None or channel not in CHANNELS:
        return None
    
    # null check
    _channel = client.get_channel(id_num(channel))
    if _channel is None:
        return None
    
    return _channel
    
    if isinstance(_channel, discord.TextChannel):
        return _channel
    return None

async def send_message(
        client: discord.Client | None,
        channel: CHANNEL_NAMES,
        message: str = "",
        allowed_mentions: bool = True,
        embed: discord.Embed | None = None
    ):
    "Sends a message to a specified channel."
    _channel = get_channel(client, channel)
    if _channel is None:
        return False
    
    mentions = discord.AllowedMentions.all() if allowed_mentions else discord.AllowedMentions.none()
    
    if embed is None:
        try:
            await _channel.send(message, allowed_mentions=mentions)
        except (aiohttp.ClientConnectionError, discord.ConnectionClosed, discord.HTTPException):
            return False
    else:
        try:
            await _channel.send(message, allowed_mentions=mentions, embed=embed)
        except (aiohttp.ClientConnectionError, discord.ConnectionClosed, discord.HTTPException):
            return False
    return True
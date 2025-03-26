from typing import Literal


IN_CE = False

CE_CHANNELS = {
    "game_additions" : 949482536726298666,
    "casino" : 1080137628604694629,
    "casino_log" : 1218980203209035938,
    "private_log" : 1208259110638985246,
    "user_log" : 1256832310523859025,
    "proof_submissions" : 747384873320448082,
    "input_log" : 0
}

CE_CHANNELS["input_log"] = CE_CHANNELS["private_log"] # temp

TEST_CHANNELS = {
    "game_additions" : 1128742486416834570,
    "casino" : 811286469251039333,
    "casino_log" : 1257381604452466737,
    "private_log" : 1141886539157221457,
    "user_log" : 1257381593136365679,
    "proof_submissions" : 1263199416462868522,
    "input_log" : 1294335132236251157
}

CHANNELS = CE_CHANNELS if IN_CE else TEST_CHANNELS

CHANNEL_NAMES = Literal["game_additions", "casino", "casino_log", "private_log", "user_log", "proof_submissions", "input_log"]

GAME_ADDITIONS_ID = CHANNELS["game_additions"]
CASINO_ID = CHANNELS["casino"]
CASINO_LOG_ID = CHANNELS["casino_log"]
PRIVATE_LOG_ID = CHANNELS['private_log']
USER_LOG_ID = CHANNELS["user_log"]
PROOF_SUBMISSIONS_ID = CHANNELS['proof_submissions']
INPUT_LOG_ID = CHANNELS['input_log']

def id_num(channel_name : CHANNEL_NAMES) :
    """
    Returns the channel ID for a given key.
    """
    return CHANNELS.get(channel_name, 0)
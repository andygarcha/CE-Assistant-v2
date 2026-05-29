import re
import pytest

from utils.icons import get_emoji
from utils.channels import id_num

EMOJI_PATTERN = re.compile(r"^<:.+:\d+>$")

TIER_KEYS = [
    "Tier 0",
    "Tier 1",
    "Tier 2",
    "Tier 3",
    "Tier 4",
    "Tier 5",
    "Tier 6",
    "Tier 7",
]
CATEGORY_KEYS = [
    "Action",
    "Arcade",
    "Bullet Hell",
    "First-Person",
    "Platformer",
    "Strategy",
]
RANK_KEYS = [
    "A Rank",
    "B Rank",
    "C Rank",
    "D Rank",
    "E Rank",
    "S Rank",
    "SS Rank",
    "SSS Rank",
    "EX Rank",
]
CHANNEL_KEYS = [
    "gameadditions",
    "casino",
    "casinolog",
    "privatelog",
    "userlog",
    "proofsubmissions",
    "inputlog",
]


# ── get_emoji ─────────────────────────────────────────────────────────────────


class TestGetEmoji:
    @pytest.mark.parametrize("key", TIER_KEYS)
    def test_tier_keys_return_emoji_format(self, key):
        assert EMOJI_PATTERN.match(get_emoji(key)), f"Bad result for {key!r}"

    @pytest.mark.parametrize("key", CATEGORY_KEYS)
    def test_category_keys_return_emoji_format(self, key):
        assert EMOJI_PATTERN.match(get_emoji(key)), f"Bad result for {key!r}"

    @pytest.mark.parametrize("key", RANK_KEYS)
    def test_rank_keys_return_emoji_format(self, key):
        assert EMOJI_PATTERN.match(get_emoji(key)), f"Bad result for {key!r}"

    def test_unknown_key_returns_bad_input(self):
        assert get_emoji("not-a-real-key") == "bad-input"  # type: ignore

    def test_tier_emojis_are_all_distinct(self):
        emojis = [get_emoji(k) for k in TIER_KEYS]  # type: ignore
        assert len(set(emojis)) == len(TIER_KEYS)

    def test_category_emojis_are_all_distinct(self):
        emojis = [get_emoji(k) for k in CATEGORY_KEYS]  # type: ignore
        assert len(set(emojis)) == len(CATEGORY_KEYS)

    def test_known_misc_keys_return_emoji_format(self):
        for key in ("Casino", "Diamond", "Points", "Arrow"):
            assert EMOJI_PATTERN.match(get_emoji(key)), f"Bad result for {key!r}"


# ── id_num ────────────────────────────────────────────────────────────────────


class TestIdNum:
    @pytest.mark.parametrize("channel", CHANNEL_KEYS)
    def test_known_channel_returns_nonzero_int(self, channel):
        result = id_num(channel)
        assert isinstance(result, int)
        assert result != 0

    def test_unknown_channel_returns_zero(self):
        assert id_num("does-not-exist") == 0  # type: ignore

    def test_all_known_channel_ids_are_discord_snowflakes(self):
        for channel in CHANNEL_KEYS:
            result = id_num(channel)  # type: ignore
            assert result > (1 << 40), (
                f"Channel {channel!r} has suspiciously small ID {result}"
            )

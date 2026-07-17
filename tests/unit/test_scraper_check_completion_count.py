from Classes.CE_User import MUTELIST_CEIDS
from tests.conftest import make_user
from web_scraper.scraper import check_completion_count

MUTED_CE_ID = MUTELIST_CEIDS[0]


def _regular_user(display_name: str = "TestUser"):
    return make_user(ce_id="user-001-0000-0000-000000000000", display_name=display_name)


def _muted_user(display_name: str = "MutedUser"):
    return make_user(ce_id=MUTED_CE_ID, display_name=display_name)


class TestCheckCompletionCountNoUpdate:
    def test_returns_none_below_first_milestone(self):
        assert check_completion_count(0, 24, _regular_user()) is None

    def test_returns_none_when_count_unchanged(self):
        assert check_completion_count(25, 25, _regular_user()) is None

    def test_returns_none_when_count_decreases(self):
        assert check_completion_count(30, 20, _regular_user()) is None

    def test_returns_none_within_same_25_band(self):
        assert check_completion_count(25, 49, _regular_user()) is None

    def test_returns_none_within_second_25_band(self):
        assert check_completion_count(50, 74, _regular_user()) is None


class TestCheckCompletionCountPublicMessage:
    def test_returns_update_crossing_25(self):
        result = check_completion_count(24, 25, _regular_user())
        assert result is not None

    def test_returns_update_crossing_50(self):
        result = check_completion_count(49, 50, _regular_user())
        assert result is not None

    def test_returns_update_crossing_75(self):
        result = check_completion_count(74, 75, _regular_user())
        assert result is not None

    def test_public_message_goes_to_userlog(self):
        result = check_completion_count(24, 25, _regular_user())
        assert result is not None
        assert result.location == "userlog"

    def test_public_message_is_not_embed(self):
        result = check_completion_count(24, 25, _regular_user())
        assert result is not None
        assert result.is_embed is False

    def test_public_message_contains_display_name(self):
        user = _regular_user("GreatPlayer")
        result = check_completion_count(24, 25, user)
        assert result is not None
        assert "GreatPlayer" in result.text

    def test_public_message_contains_milestone_number(self):
        result = check_completion_count(24, 25, _regular_user())
        assert result is not None
        assert "25" in result.text

    def test_public_message_milestone_reflects_new_count(self):
        result = check_completion_count(49, 50, _regular_user())
        assert result is not None
        assert "50" in result.text


class TestCheckCompletionCountMutedMessage:
    def test_muted_user_crossing_milestone_returns_update(self):
        result = check_completion_count(24, 25, _muted_user())
        assert result is not None

    def test_muted_message_goes_to_privatelog(self):
        result = check_completion_count(24, 25, _muted_user())
        assert result is not None
        assert result.location == "privatelog"

    def test_muted_message_is_not_embed(self):
        result = check_completion_count(24, 25, _muted_user())
        assert result is not None
        assert result.is_embed is False

    def test_muted_message_contains_display_name_with_link(self):
        user = _muted_user("SneakyPlayer")
        result = check_completion_count(24, 25, user)
        assert result is not None
        assert user.display_name_with_link in result.text

    def test_muted_message_contains_milestone_number(self):
        result = check_completion_count(24, 25, _muted_user())
        assert result is not None
        assert "25" in result.text


# ── allowed_mentions gating (ping_user_log) ──────────────────────────────────


def _pref_user(ping_user_log: bool, discord_id: int = 999):
    return make_user(
        ce_id="user-001-0000-0000-000000000000",
        discord_id=discord_id,
        ping_user_log=ping_user_log,
    )


def _muted_pref_user(ping_user_log: bool):
    return make_user(ce_id=MUTED_CE_ID, ping_user_log=ping_user_log)


class TestAllowedMentionsMilestone:
    def test_pings_when_opted_in(self):
        result = check_completion_count(24, 25, _pref_user(True))
        assert result is not None
        assert result.allowed_mentions == [999]

    def test_no_ping_when_opted_out(self):
        result = check_completion_count(24, 25, _pref_user(False))
        assert result is not None
        assert result.allowed_mentions == []

    def test_muted_user_never_pings_even_when_opted_in(self):
        result = check_completion_count(24, 25, _muted_pref_user(True))
        assert result is not None
        assert result.location == "privatelog"
        assert result.allowed_mentions == []

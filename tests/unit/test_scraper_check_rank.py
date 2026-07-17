from Classes.CE_User import MUTELIST_CEIDS
from tests.conftest import make_user
from web_scraper.scraper import check_rank

MUTED_CE_ID = MUTELIST_CEIDS[0]


def _regular_user(display_name: str = "TestUser"):
    return make_user(ce_id="user-001-0000-0000-000000000000", display_name=display_name)


def _muted_user(display_name: str = "MutedUser"):
    return make_user(ce_id=MUTED_CE_ID, display_name=display_name)


class TestCheckRankNoUpdate:
    def test_returns_none_when_rank_unchanged(self):
        user = _regular_user()
        assert check_rank("B Rank", "B Rank", 400, 500, user) is None

    def test_returns_none_when_points_did_not_increase(self):
        user = _regular_user()
        assert check_rank("B Rank", "A Rank", 500, 500, user) is None

    def test_returns_none_when_points_decreased(self):
        user = _regular_user()
        assert check_rank("B Rank", "A Rank", 600, 500, user) is None

    def test_returns_none_when_rank_unchanged_and_points_decreased(self):
        user = _regular_user()
        assert check_rank("A Rank", "A Rank", 600, 500, user) is None


class TestCheckRankPublicMessage:
    def test_returns_update_on_rank_up_with_point_increase(self):
        user = _regular_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None

    def test_public_message_goes_to_userlog(self):
        user = _regular_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert result.location == "userlog"

    def test_public_message_is_not_embed(self):
        user = _regular_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert result.is_embed is False

    def test_public_message_contains_user_mention(self):
        user = _regular_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert user.mention in result.text

    def test_public_message_contains_display_name(self):
        user = _regular_user("AwesomePlayer")
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert "AwesomePlayer" in result.text

    def test_public_message_contains_old_and_new_rank(self):
        user = _regular_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert "Rank" in result.text


class TestCheckRankMutedMessage:
    def test_muted_user_rank_up_returns_update(self):
        user = _muted_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None

    def test_muted_message_goes_to_privatelog(self):
        user = _muted_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert result.location == "privatelog"

    def test_muted_message_is_not_embed(self):
        user = _muted_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert result.is_embed is False

    def test_muted_message_contains_display_name_with_link(self):
        user = _muted_user("SneakyUser")
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert user.display_name_with_link in result.text

    def test_muted_message_contains_old_and_new_rank(self):
        user = _muted_user()
        result = check_rank("B Rank", "A Rank", 400, 1000, user)
        assert result is not None
        assert "B Rank" in result.text
        assert "A Rank" in result.text


# ── allowed_mentions gating (ping_user_log) ──────────────────────────────────


def _pref_user(ping_user_log: bool, discord_id: int = 999):
    return make_user(
        ce_id="user-001-0000-0000-000000000000",
        discord_id=discord_id,
        ping_user_log=ping_user_log,
    )


def _muted_pref_user(ping_user_log: bool):
    return make_user(ce_id=MUTED_CE_ID, ping_user_log=ping_user_log)


class TestAllowedMentionsRankUp:
    def test_pings_when_opted_in(self):
        result = check_rank("B Rank", "A Rank", 400, 1000, _pref_user(True))
        assert result is not None
        assert result.allowed_mentions == [999]

    def test_no_ping_when_opted_out(self):
        result = check_rank("B Rank", "A Rank", 400, 1000, _pref_user(False))
        assert result is not None
        assert result.allowed_mentions == []

    def test_muted_user_never_pings_even_when_opted_in(self):
        result = check_rank("B Rank", "A Rank", 400, 1000, _muted_pref_user(True))
        assert result is not None
        assert result.location == "privatelog"
        assert result.allowed_mentions == []

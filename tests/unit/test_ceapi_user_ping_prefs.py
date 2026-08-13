import datetime

from Classes.CE_User import CEAPIUser
from tests.conftest import make_user
from web_scraper.scraper import _backfill_supabase_fields


def _api_user(**ping_kwargs) -> CEAPIUser:
    return CEAPIUser(
        discord_id=0,
        ce_id="user-001-0000-0000-000000000000",
        owned_games=[],
        rolls=[],
        full_data={},
        display_name="TestUser",
        avatar="",
        last_updated=datetime.datetime.now(datetime.UTC),
        **ping_kwargs,
    )


class TestCEAPIUserPingPreferences:
    def test_defaults_to_false(self):
        user = _api_user()
        assert user.ping_casino_fail is False
        assert user.ping_casino_win is False
        assert user.ping_user_log is False
        assert user.casino_fail_pingable_ids == []

    def test_forwards_ping_preferences_to_base_class(self):
        user = _api_user(
            ping_casino_fail=True, ping_casino_win=True, ping_user_log=True
        )
        assert user.ping_casino_fail is True
        assert user.ping_casino_win is True
        assert user.ping_user_log is True
        assert user.casino_fail_pingable_ids == [0]
        assert user.casino_win_pingable_ids == [0]
        assert user.user_log_pingable_ids == [0]


class TestBackfillSupabaseFields:
    def test_ping_preferences_are_copied_from_supabase_user(self):
        user_old = make_user(
            discord_id=123,
            ping_casino_fail=True,
            ping_casino_win=True,
            ping_user_log=True,
        )
        user_new = _api_user()

        _backfill_supabase_fields(user_new, user_old)

        assert user_new.discord_id == 123
        assert user_new.ping_casino_fail is True
        assert user_new.ping_casino_win is True
        assert user_new.ping_user_log is True
        assert user_new.casino_fail_pingable_ids == [123]

    def test_false_preferences_are_also_copied(self):
        user_old = make_user(discord_id=456)
        user_new = _api_user(
            ping_casino_fail=True, ping_casino_win=True, ping_user_log=True
        )

        _backfill_supabase_fields(user_new, user_old)

        assert user_new.ping_casino_fail is False
        assert user_new.ping_casino_win is False
        assert user_new.ping_user_log is False

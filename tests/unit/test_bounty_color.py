"""Tests for the bounty-color feature: SupabaseReader's
add_user_bounty_color/get_user_bounty_colors, and LocalCache's
bounty_color table plumbing.

Like every other table in SupabaseReader.py, reads go through the
LocalCache SQLite mirror rather than hitting Supabase live, and
add_user_bounty_color() dual-writes to both Supabase and LocalCache. The
table is also wired into LocalCache.rebuild_from_supabase()'s table map and
run_integrity_check()'s users child-sync/cascade-delete, so it self-heals
the same way every other table does (see Modules/LocalCache.py).
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

from Modules import LocalCache, SupabaseReader


def _init_cache() -> str:
    tmpdir = tempfile.mkdtemp()
    LocalCache.init(os.path.join(tmpdir, "test.db"))
    return tmpdir


def _teardown_cache(tmpdir: str) -> None:
    LocalCache.close()
    shutil.rmtree(tmpdir)


def _mock_supabase() -> MagicMock:
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_table.upsert.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])
    mock_sb.table.return_value = mock_table
    return mock_sb


class TestGetUserBountyColorsReadsFromCache:
    def test_returns_empty_when_none_granted(self):
        tmpdir = _init_cache()
        try:
            assert SupabaseReader.get_user_bounty_colors("u1") == []
        finally:
            _teardown_cache(tmpdir)

    def test_returns_seeded_rows_without_touching_supabase(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_bounty_colors_bulk(
                [{"user_id": "u1", "color_name": "Cotton Candy"}]
            )
            mock_sb = MagicMock()
            with patch("Modules.SupabaseReader.supabase", mock_sb):
                result = SupabaseReader.get_user_bounty_colors("u1")
            assert result == ["Cotton Candy"]
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)

    def test_only_returns_colors_for_the_requested_user(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_bounty_colors_bulk(
                [
                    {"user_id": "u1", "color_name": "Cotton Candy"},
                    {"user_id": "u2", "color_name": "Aquamarine"},
                ]
            )
            assert SupabaseReader.get_user_bounty_colors("u1") == ["Cotton Candy"]
        finally:
            _teardown_cache(tmpdir)


class TestAddUserBountyColorDualWrite:
    def test_writes_to_local_cache(self):
        tmpdir = _init_cache()
        try:
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.add_user_bounty_color("u1", "Cotton Candy")
            assert LocalCache.get_bounty_colors("u1") == ["Cotton Candy"]
        finally:
            _teardown_cache(tmpdir)

    def test_writes_to_supabase(self):
        tmpdir = _init_cache()
        try:
            mock_sb = _mock_supabase()
            with patch("Modules.SupabaseReader.supabase", mock_sb):
                SupabaseReader.add_user_bounty_color("u1", "Cotton Candy")
            mock_sb.table.assert_called_with("bounty_color")
            mock_sb.table.return_value.upsert.assert_called_once_with(
                {"user_id": "u1", "color_name": "Cotton Candy"}
            )
        finally:
            _teardown_cache(tmpdir)

    def test_a_read_immediately_after_a_grant_sees_it_via_cache_only(self):
        tmpdir = _init_cache()
        try:
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.add_user_bounty_color("u1", "Cotton Candy")
                # no supabase mock needed for the read -- proves it never
                # goes back out to Supabase after a write
                result = SupabaseReader.get_user_bounty_colors("u1")
            assert result == ["Cotton Candy"]
        finally:
            _teardown_cache(tmpdir)

    def test_granting_the_same_color_twice_does_not_duplicate_locally(self):
        tmpdir = _init_cache()
        try:
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.add_user_bounty_color("u1", "Cotton Candy")
                SupabaseReader.add_user_bounty_color("u1", "Cotton Candy")
            assert LocalCache.get_bounty_colors("u1") == ["Cotton Candy"]
        finally:
            _teardown_cache(tmpdir)

    def test_granting_multiple_colors_keeps_them_all(self):
        tmpdir = _init_cache()
        try:
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.add_user_bounty_color("u1", "Cotton Candy")
                SupabaseReader.add_user_bounty_color("u1", "Aquamarine")
            assert sorted(LocalCache.get_bounty_colors("u1")) == [
                "Aquamarine",
                "Cotton Candy",
            ]
        finally:
            _teardown_cache(tmpdir)


class TestDegradedColorNamesPassThroughUnfiltered:
    """LocalCache/SupabaseReader do no validation against
    utils.channels.BOUNTY_COLORS -- that filtering happens one layer up in
    commands.user.set_color (see TestStaleBountyColorIsSkippedNotCrashed and
    TestMissingRoleRaises in test_set_color.py) and in
    commands.admin.assign_bounty_color, which only ever grants a name it
    already validated. If a color is later renamed or removed from
    BOUNTY_COLORS, the row already stored in Supabase/LocalCache is now
    "degraded" (no longer a recognized color name) -- this layer must still
    round-trip it exactly as stored, not silently drop or choke on it,
    since dropping it here (instead of at the display layer) would make it
    impossible to distinguish "never granted" from "granted but now stale"."""

    def test_get_user_bounty_colors_returns_a_name_not_in_BOUNTY_COLORS(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_bounty_colors_bulk(
                [{"user_id": "u1", "color_name": "Extinct Color"}]
            )
            assert SupabaseReader.get_user_bounty_colors("u1") == ["Extinct Color"]
        finally:
            _teardown_cache(tmpdir)

    def test_add_user_bounty_color_does_not_validate_against_BOUNTY_COLORS(self):
        tmpdir = _init_cache()
        try:
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.add_user_bounty_color("u1", "Not A Real Color")
            assert LocalCache.get_bounty_colors("u1") == ["Not A Real Color"]
        finally:
            _teardown_cache(tmpdir)

    def test_degraded_and_valid_colors_both_round_trip_together(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_bounty_colors_bulk(
                [
                    {"user_id": "u1", "color_name": "Cotton Candy"},
                    {"user_id": "u1", "color_name": "Extinct Color"},
                ]
            )
            assert sorted(SupabaseReader.get_user_bounty_colors("u1")) == [
                "Cotton Candy",
                "Extinct Color",
            ]
        finally:
            _teardown_cache(tmpdir)


class TestBountyColorUpsertBulk:
    """rebuild_from_supabase() and run_integrity_check() both sync
    bounty_color through LocalCache.upsert_bounty_colors_bulk() (see
    _UPSERT_BULK_FUNCS in LocalCache.py) -- rebuild_from_supabase() itself
    is globally patched to a no-op for this whole test session (see
    tests/conftest.py, to avoid real network calls at import time), so this
    tests the bulk-upsert entry point those two callers actually use."""

    def test_populates_bounty_color_from_supabase_shaped_rows(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_bounty_colors_bulk(
                [{"user_id": "u1", "color_name": "Cotton Candy"}]
            )
            assert LocalCache.get_bounty_colors("u1") == ["Cotton Candy"]
        finally:
            _teardown_cache(tmpdir)

    def test_empty_list_is_a_no_op(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_bounty_colors_bulk([])
            assert LocalCache.get_bounty_colors("u1") == []
        finally:
            _teardown_cache(tmpdir)

    def test_is_registered_in_the_rebuild_dispatch_table(self):
        assert "bounty_color" in LocalCache._UPSERT_BULK_FUNCS
        assert (
            LocalCache._UPSERT_BULK_FUNCS["bounty_color"]
            is LocalCache.upsert_bounty_colors_bulk
        )

    def test_is_registered_as_a_child_sync_of_users(self):
        child_tables = [c[2] for c in LocalCache._CHILD_SYNCS["users"]]
        assert "bounty_color" in child_tables


class TestBountyColorCascadeDelete:
    """run_integrity_check() removes bounty_color rows for any user that's
    gone stale locally (deleted from Supabase), matching how user_games and
    user_objectives are cascade-deleted in the same code path."""

    def test_stale_user_removes_their_bounty_colors(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_user(
                {
                    "ce_id": "u1",
                    "discord_id": 1,
                    "display_name": "Andy",
                    "image_avatar": None,
                    "steam_id": None,
                    "created_at_CE": "",
                    "updated_at_CE": "",
                }
            )
            LocalCache.upsert_bounty_colors_bulk(
                [{"user_id": "u1", "color_name": "Cotton Candy"}]
            )

            # run_integrity_check() does `from Modules.SupabaseReader import
            # supabase as sb` internally, so patching that module attribute
            # is what it sees. Every table lookup returns no rows here, i.e.
            # everything currently in LocalCache (including "u1") is stale.
            mock_sb = MagicMock()
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.range.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])
            mock_sb.table.return_value = mock_table

            with patch("Modules.SupabaseReader.supabase", mock_sb):
                LocalCache.run_integrity_check()

            assert LocalCache.get_bounty_colors("u1") == []
        finally:
            _teardown_cache(tmpdir)

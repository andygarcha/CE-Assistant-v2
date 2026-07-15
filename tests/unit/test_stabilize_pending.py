from unittest.mock import patch

from tests.conftest import make_game, make_objective
from web_scraper.scraper import (
    finalize_stabilized_game_update,
    stabilize_pending_updates,
)


def _run(pending: list[dict], changed: set[str]) -> list | None:
    """Run stabilize_pending_updates and return the IDs passed to promote, or None if not called."""
    with (
        patch(
            "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
            return_value=pending,
        ),
        patch(
            "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
            return_value=None,
        ),
        patch(
            "web_scraper.scraper.SupabaseReader.promote_pending_to_stable"
        ) as mock_promote,
    ):
        stabilize_pending_updates(changed)

    if mock_promote.called:
        return mock_promote.call_args[0][0]
    return None


class TestStabilizeBasicRouting:
    """Core contract: unchanged games get promoted, changed games don't."""

    def test_unchanged_game_promoted(self):
        promoted = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001"}],
            changed=set(),
        )
        assert promoted == ["p1"]

    def test_changed_game_not_promoted(self):
        promoted = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001"}],
            changed={"game-001"},
        )
        assert promoted is None

    def test_mixed_batch_only_unchanged_promoted(self):
        promoted = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-002"},
                {"id": "p3", "game_ce_id": "game-003"},
            ],
            changed={"game-002"},
        )
        assert promoted is not None
        assert "p1" in promoted
        assert "p2" not in promoted
        assert "p3" in promoted


class TestStabilizeEmptyInputs:
    def test_no_pending_updates(self):
        promoted = _run(pending=[], changed={"game-001"})
        assert promoted is None

    def test_no_changed_games_promotes_all(self):
        promoted = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-002"},
            ],
            changed=set(),
        )
        assert promoted is not None
        assert set(promoted) == {"p1", "p2"}

    def test_both_empty(self):
        promoted = _run(pending=[], changed=set())
        assert promoted is None

    def test_all_pending_are_changed(self):
        promoted = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-002"},
            ],
            changed={"game-001", "game-002"},
        )
        assert promoted is None


class TestStabilizeMultipleRowsSameGame:
    """A game could have multiple pending rows if e.g. it was removed and re-added,
    or if upsert created separate rows for different update types.
    All rows for the same game should follow the same fate."""

    def test_two_rows_same_unchanged_game_both_promoted(self):
        promoted = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-001"},
            ],
            changed=set(),
        )
        assert promoted is not None
        assert set(promoted) == {"p1", "p2"}

    def test_two_rows_same_changed_game_neither_promoted(self):
        promoted = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-001"},
            ],
            changed={"game-001"},
        )
        assert promoted is None

    def test_mixed_some_games_have_multiple_rows(self):
        promoted = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-stable"},
                {"id": "p2", "game_ce_id": "game-stable"},
                {"id": "p3", "game_ce_id": "game-changing"},
                {"id": "p4", "game_ce_id": "game-also-stable"},
            ],
            changed={"game-changing"},
        )
        assert promoted is not None
        assert set(promoted) == {"p1", "p2", "p4"}
        assert "p3" not in promoted


class TestStabilizeIrrelevantChangedIds:
    """changed_game_ids may contain IDs that don't match any pending update.
    This must not affect promotion of unrelated pending rows."""

    def test_changed_set_has_ids_not_in_pending(self):
        promoted = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001"}],
            changed={"game-999", "game-888"},
        )
        assert promoted == ["p1"]

    def test_changed_set_is_superset_of_pending(self):
        promoted = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001"}],
            changed={"game-001", "game-002", "game-003"},
        )
        assert promoted is None

    def test_large_changed_set_with_one_matching(self):
        large_changed = {f"game-{i:04d}" for i in range(500)}
        large_changed.add("game-match")
        promoted = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-match"},
                {"id": "p2", "game_ce_id": "game-safe"},
            ],
            changed=large_changed,
        )
        assert promoted == ["p2"]


class TestStabilizeIdMatching:
    """The game_ce_id comparison must be exact string equality, not substring or prefix."""

    def test_substring_ids_do_not_match(self):
        promoted = _run(
            pending=[{"id": "p1", "game_ce_id": "game-1"}],
            changed={"game-10", "game-100"},
        )
        assert promoted == ["p1"]

    def test_prefix_ids_do_not_match(self):
        promoted = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001-extra"}],
            changed={"game-001"},
        )
        assert promoted == ["p1"]

    def test_case_sensitive_matching(self):
        promoted = _run(
            pending=[{"id": "p1", "game_ce_id": "Game-001"}],
            changed={"game-001"},
        )
        assert promoted == ["p1"]


class TestStabilizePromoteCallShape:
    """Verify the promote call is made correctly — single call with all IDs."""

    def test_single_promote_call_for_multiple_ids(self):
        pending = [
            {"id": "p1", "game_ce_id": "game-001"},
            {"id": "p2", "game_ce_id": "game-002"},
            {"id": "p3", "game_ce_id": "game-003"},
        ]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
                return_value=pending,
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=None,
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.promote_pending_to_stable"
            ) as mock_promote,
        ):
            stabilize_pending_updates(set())

        assert mock_promote.call_count == 1
        assert len(mock_promote.call_args[0][0]) == 3

    def test_preserves_row_order_from_pending(self):
        pending = [
            {"id": "z9", "game_ce_id": "game-z"},
            {"id": "a1", "game_ce_id": "game-a"},
            {"id": "m5", "game_ce_id": "game-m"},
        ]

        promoted = _run(pending=pending, changed=set())
        assert promoted == ["z9", "a1", "m5"]


class TestFinalizeStabilizedGameUpdate:
    def test_no_snapshot_returns_false_and_writes_nothing(self):
        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=None,
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update"
            ) as mock_write,
            patch(
                "web_scraper.scraper.SupabaseReader.delete_pending_game_snapshot"
            ) as mock_delete,
        ):
            result = finalize_stabilized_game_update("game-001")

        assert result is False
        mock_write.assert_not_called()
        mock_delete.assert_not_called()

    def test_real_diff_writes_stable_row_and_deletes_snapshot(self):
        snapshot = make_game(
            ce_id="game-001",
            objectives=[make_objective(ce_id="obj-a", point_value=10)],
        )
        current = make_game(
            ce_id="game-001",
            objectives=[make_objective(ce_id="obj-a", point_value=20)],
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=snapshot,
            ),
            patch("web_scraper.scraper.SupabaseReader.get_game", return_value=current),
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update"
            ) as mock_write,
            patch(
                "web_scraper.scraper.SupabaseReader.delete_pending_game_snapshot"
            ) as mock_delete,
        ):
            result = finalize_stabilized_game_update("game-001")

        assert result is True
        mock_write.assert_called_once()
        written_row = mock_write.call_args[0][0]
        assert written_row["game_ce_id"] == "game-001"
        assert written_row["status"] == "stable"
        mock_delete.assert_called_once_with("game-001")

    def test_net_zero_diff_writes_nothing_but_still_cleans_up(self):
        """Points went up then back down across loops -- snapshot vs final
        state shows no real change. Don't post a misleading empty message,
        but still clear the snapshot so it doesn't leak forever."""
        same_game = make_game(
            ce_id="game-001",
            objectives=[make_objective(ce_id="obj-a", point_value=10)],
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=same_game,
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.get_game",
                return_value=make_game(
                    ce_id="game-001",
                    objectives=[make_objective(ce_id="obj-a", point_value=10)],
                ),
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update"
            ) as mock_write,
            patch(
                "web_scraper.scraper.SupabaseReader.delete_pending_game_snapshot"
            ) as mock_delete,
        ):
            result = finalize_stabilized_game_update("game-001")

        assert result is True
        mock_write.assert_not_called()
        mock_delete.assert_called_once_with("game-001")

    def test_current_game_missing_still_cleans_up_snapshot(self):
        """Game was removed entirely while its update was still pending."""
        snapshot = make_game(ce_id="game-001")

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=snapshot,
            ),
            patch("web_scraper.scraper.SupabaseReader.get_game", return_value=None),
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update"
            ) as mock_write,
            patch(
                "web_scraper.scraper.SupabaseReader.delete_pending_game_snapshot"
            ) as mock_delete,
        ):
            result = finalize_stabilized_game_update("game-001")

        assert result is True
        mock_write.assert_not_called()
        mock_delete.assert_called_once_with("game-001")


class TestStabilizeUsesFinalize:
    def test_promoted_game_with_snapshot_deletes_stale_row_not_promotes_it(self):
        pending = [{"id": "p1", "game_ce_id": "game-001"}]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
                return_value=pending,
            ),
            patch(
                "web_scraper.scraper.finalize_stabilized_game_update",
                return_value=True,
            ) as mock_finalize,
            patch(
                "web_scraper.scraper.SupabaseReader.promote_pending_to_stable"
            ) as mock_promote,
            patch(
                "web_scraper.scraper.SupabaseReader.delete_stale_pending_update"
            ) as mock_delete_stale,
        ):
            stabilize_pending_updates(set())

        mock_finalize.assert_called_once_with("game-001")
        mock_promote.assert_not_called()
        mock_delete_stale.assert_called_once_with("p1")

    def test_promoted_game_without_snapshot_falls_back_to_promote(self):
        pending = [{"id": "p1", "game_ce_id": "game-001"}]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
                return_value=pending,
            ),
            patch(
                "web_scraper.scraper.finalize_stabilized_game_update",
                return_value=False,
            ) as mock_finalize,
            patch(
                "web_scraper.scraper.SupabaseReader.promote_pending_to_stable"
            ) as mock_promote,
        ):
            stabilize_pending_updates(set())

        mock_finalize.assert_called_once_with("game-001")
        mock_promote.assert_called_once_with(["p1"])

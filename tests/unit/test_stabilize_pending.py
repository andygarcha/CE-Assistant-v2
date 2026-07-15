import asyncio
from unittest.mock import AsyncMock, patch

from tests.conftest import make_api_game, make_game, make_objective
from web_scraper.scraper import (
    finalize_stabilized_game_update,
    stabilize_pending_updates,
)


def _run(pending: list[dict], changed: set[str]) -> list | None:
    """Run stabilize_pending_updates and return the IDs passed to delete_stale_pending_update, or None if not called."""
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
            "web_scraper.scraper.CEAPIReader.get_game",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "web_scraper.scraper.SupabaseReader.delete_stale_pending_update"
        ) as mock_delete,
    ):
        asyncio.run(stabilize_pending_updates(changed))

    if mock_delete.called:
        return [call.args[0] for call in mock_delete.call_args_list]
    return None


class TestStabilizeBasicRouting:
    """Core contract: unchanged games get finalized (and their stale pending
    row removed), changed games are left pending."""

    def test_unchanged_game_finalized(self):
        finalized = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001"}],
            changed=set(),
        )
        assert finalized == ["p1"]

    def test_changed_game_not_finalized(self):
        finalized = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001"}],
            changed={"game-001"},
        )
        assert finalized is None

    def test_mixed_batch_only_unchanged_finalized(self):
        finalized = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-002"},
                {"id": "p3", "game_ce_id": "game-003"},
            ],
            changed={"game-002"},
        )
        assert finalized is not None
        assert set(finalized) == {"p1", "p3"}


class TestStabilizeMultipleRowsSameGame:
    """A game could have multiple pending rows if e.g. it was removed and re-added,
    or if upsert created separate rows for different update types.
    All rows for the same game should follow the same fate."""

    def test_two_rows_same_unchanged_game_both_finalized(self):
        finalized = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-001"},
            ],
            changed=set(),
        )
        assert finalized is not None
        assert set(finalized) == {"p1", "p2"}

    def test_two_rows_same_changed_game_neither_finalized(self):
        finalized = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-001"},
            ],
            changed={"game-001"},
        )
        assert finalized is None


class TestStabilizeIdMatching:
    """The game_ce_id comparison must be exact string equality, not substring or prefix."""

    def test_substring_ids_do_not_match(self):
        finalized = _run(
            pending=[{"id": "p1", "game_ce_id": "game-1"}],
            changed={"game-10", "game-100"},
        )
        assert finalized == ["p1"]

    def test_prefix_ids_do_not_match(self):
        finalized = _run(
            pending=[{"id": "p1", "game_ce_id": "game-001-extra"}],
            changed={"game-001"},
        )
        assert finalized == ["p1"]

    def test_case_sensitive_matching(self):
        finalized = _run(
            pending=[{"id": "p1", "game_ce_id": "Game-001"}],
            changed={"game-001"},
        )
        assert finalized == ["p1"]


class TestStabilizeEmptyInputs:
    def test_no_pending_updates(self):
        finalized = _run(pending=[], changed={"game-001"})
        assert finalized is None

    def test_both_empty(self):
        finalized = _run(pending=[], changed=set())
        assert finalized is None

    def test_all_pending_are_changed(self):
        finalized = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-001"},
                {"id": "p2", "game_ce_id": "game-002"},
            ],
            changed={"game-001", "game-002"},
        )
        assert finalized is None


class TestFinalizeStabilizedGameUpdate:
    def test_no_snapshot_and_game_gone_writes_nothing(self):
        """No snapshot (new game) and the game is no longer on the site --
        nothing to send."""
        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=None,
            ),
            patch(
                "web_scraper.scraper.CEAPIReader.get_game",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update"
            ) as mock_write,
        ):
            asyncio.run(finalize_stabilized_game_update("game-001"))

        mock_write.assert_not_called()

    def test_no_snapshot_regenerates_new_game_message_from_fresh_data(self):
        """No snapshot means this was a new game. Its message should be
        rebuilt from a fresh CEAPIGame fetch (which has gameTags), not
        whatever was captured on the loop it was first detected (which may
        have come from a full_scrape hit, where /api/games/full omits
        gameTags entirely)."""
        fresh_game = make_api_game(
            ce_id="game-001",
            game_tags=[
                {"tagId": "t1", "tag": {"name": "Tower Defense", "type": "genre"}}
            ],
        )
        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=None,
            ),
            patch(
                "web_scraper.scraper.CEAPIReader.get_game",
                new_callable=AsyncMock,
                return_value=fresh_game,
            ) as mock_get_game,
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update"
            ) as mock_write,
        ):
            asyncio.run(finalize_stabilized_game_update("game-001"))

        mock_get_game.assert_called_once_with("game-001")
        mock_write.assert_called_once()
        written_row = mock_write.call_args[0][0]
        assert written_row["game_ce_id"] == "game-001"
        assert written_row["status"] == "stable"
        assert "Genre tags: Tower Defense" in written_row["description"]

    def test_no_snapshot_hidden_game_writes_nothing(self):
        """No snapshot (new game), but the game is hidden/unfinished by the
        time we re-fetch it -- must not bypass the is_finished filter that
        every other new-game path in the file enforces."""
        hidden_game = make_api_game(ce_id="game-001", is_finished=False)
        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_snapshot",
                return_value=None,
            ),
            patch(
                "web_scraper.scraper.CEAPIReader.get_game",
                new_callable=AsyncMock,
                return_value=hidden_game,
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update"
            ) as mock_write,
        ):
            asyncio.run(finalize_stabilized_game_update("game-001"))

        mock_write.assert_not_called()

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
            asyncio.run(finalize_stabilized_game_update("game-001"))

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
            asyncio.run(finalize_stabilized_game_update("game-001"))

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
            asyncio.run(finalize_stabilized_game_update("game-001"))

        mock_write.assert_not_called()
        mock_delete.assert_called_once_with("game-001")


class TestStabilizeUsesFinalize:
    def test_finalized_game_deletes_stale_pending_row(self):
        pending = [{"id": "p1", "game_ce_id": "game-001"}]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
                return_value=pending,
            ),
            patch(
                "web_scraper.scraper.finalize_stabilized_game_update",
                new_callable=AsyncMock,
            ) as mock_finalize,
            patch(
                "web_scraper.scraper.SupabaseReader.delete_stale_pending_update"
            ) as mock_delete_stale,
        ):
            asyncio.run(stabilize_pending_updates(set()))

        mock_finalize.assert_called_once_with("game-001")
        mock_delete_stale.assert_called_once_with("p1")

    def test_preserves_row_order(self):
        pending = [
            {"id": "z9", "game_ce_id": "game-z"},
            {"id": "a1", "game_ce_id": "game-a"},
            {"id": "m5", "game_ce_id": "game-m"},
        ]

        finalized = _run(pending=pending, changed=set())
        assert finalized == ["z9", "a1", "m5"]

    def test_large_changed_set_with_one_matching(self):
        large_changed = {f"game-{i:04d}" for i in range(500)}
        large_changed.add("game-match")
        finalized = _run(
            pending=[
                {"id": "p1", "game_ce_id": "game-match"},
                {"id": "p2", "game_ce_id": "game-safe"},
            ],
            changed=large_changed,
        )
        assert finalized == ["p2"]


class TestStabilizeErrorIsolation:
    """A single row's finalize failure (e.g. a transient CE API error while
    re-fetching a new game) must not abort the rest of the batch, and the
    failing row must stay pending so it's retried next loop."""

    def test_failing_row_is_not_deleted_but_others_still_are(self):
        pending = [
            {"id": "p1", "game_ce_id": "game-fails"},
            {"id": "p2", "game_ce_id": "game-ok"},
        ]

        async def _finalize(game_ce_id: str) -> None:
            if game_ce_id == "game-fails":
                raise RuntimeError("transient CE API error")

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
                return_value=pending,
            ),
            patch(
                "web_scraper.scraper.finalize_stabilized_game_update",
                side_effect=_finalize,
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.delete_stale_pending_update"
            ) as mock_delete,
        ):
            asyncio.run(stabilize_pending_updates(set()))

        mock_delete.assert_called_once_with("p2")

    def test_failing_row_does_not_raise_out_of_stabilize(self):
        pending = [{"id": "p1", "game_ce_id": "game-fails"}]

        async def _finalize(game_ce_id: str) -> None:
            raise RuntimeError("boom")

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
                return_value=pending,
            ),
            patch(
                "web_scraper.scraper.finalize_stabilized_game_update",
                side_effect=_finalize,
            ),
            patch("web_scraper.scraper.SupabaseReader.delete_stale_pending_update"),
        ):
            asyncio.run(stabilize_pending_updates(set()))  # must not raise

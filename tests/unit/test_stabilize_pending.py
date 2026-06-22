from unittest.mock import patch
from web_scraper.scraper import stabilize_pending_updates


def _run(pending: list[dict], changed: set[str]) -> list | None:
    """Run stabilize_pending_updates and return the IDs passed to promote, or None if not called."""
    with (
        patch(
            "web_scraper.scraper.SupabaseReader.get_pending_game_updates",
            return_value=pending,
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

from web_scraper.scraper import (
    UpdateMessageForScraperProcess,
    should_snapshot_pending_game,
)


class TestShouldSnapshotPendingGame:
    def test_real_update_with_no_existing_snapshot_should_snapshot(self):
        update = UpdateMessageForScraperProcess(game_ce_id="game-001")
        assert should_snapshot_pending_game("game-001", update, set()) is True

    def test_real_update_with_existing_snapshot_should_not_resnapshot(self):
        update = UpdateMessageForScraperProcess(game_ce_id="game-001")
        assert should_snapshot_pending_game("game-001", update, {"game-001"}) is False

    def test_ghost_update_should_not_snapshot(self):
        """update_one_game returned None (no real diff) -- nothing changed,
        so there's nothing to snapshot."""
        assert should_snapshot_pending_game("game-001", None, set()) is False

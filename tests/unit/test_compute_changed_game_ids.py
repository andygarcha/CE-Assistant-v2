from web_scraper.scraper import UpdateMessageForScraperProcess, compute_changed_game_ids


def _update(game_ce_id: str | None) -> UpdateMessageForScraperProcess:
    return UpdateMessageForScraperProcess(game_ce_id=game_ce_id)


class TestComputeChangedGameIds:
    """changed_game_ids should reflect games that actually produced an
    UpdateMessageForScraperProcess, not just games whose updatedAt ticked."""

    def test_game_with_real_update_is_changed(self):
        changed = compute_changed_game_ids(
            updates=[_update("game-001")],
            removed_games=set(),
        )
        assert changed == {"game-001"}

    def test_ghost_update_does_not_count_as_changed(self):
        """A game whose updatedAt ticked but produced no real diff
        (create_update_updated_game returned None) must NOT block its
        pending row from being promoted."""
        changed = compute_changed_game_ids(
            updates=[],
            removed_games=set(),
        )
        assert changed == set()

    def test_removed_games_always_count_as_changed(self):
        changed = compute_changed_game_ids(
            updates=[],
            removed_games={"game-999"},
        )
        assert changed == {"game-999"}

    def test_mixed_real_updates_and_removed_games(self):
        changed = compute_changed_game_ids(
            updates=[_update("game-001"), _update("game-002")],
            removed_games={"game-999"},
        )
        assert changed == {"game-001", "game-002", "game-999"}

    def test_updates_without_game_ce_id_are_ignored(self):
        """Non-game updates (e.g. user/roll updates) have game_ce_id=None and
        must not pollute the changed set."""
        changed = compute_changed_game_ids(
            updates=[_update(None), _update("game-001")],
            removed_games=set(),
        )
        assert changed == {"game-001"}

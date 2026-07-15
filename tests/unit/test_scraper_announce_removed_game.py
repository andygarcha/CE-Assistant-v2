import asyncio
from unittest.mock import patch

from tests.conftest import make_game
from web_scraper.scraper import announce_removed_game

GAME_ID = "game-001-0000-0000-000000000000"


def _run(send_updates: bool = True):
    game = make_game(ce_id=GAME_ID, game_name="Doomed Game")
    with (
        patch("web_scraper.scraper.SupabaseReader.delete_game") as mock_delete,
        patch("web_scraper.scraper.SupabaseReader.write_scraper_update") as mock_write,
    ):
        asyncio.run(announce_removed_game(game, send_updates))
    return mock_delete, mock_write


class TestAnnounceRemovedGame:
    def test_deletes_the_game(self):
        mock_delete, _mock_write = _run()
        mock_delete.assert_called_once_with(GAME_ID)

    def test_writes_directly_as_stable_not_pending(self):
        """Removal announcements bypass the pending/stabilize debounce
        entirely -- there's no "after" state to diff against, so nothing
        would ever stabilize them (see the docstring on announce_removed_game
        for why the old pending-routed behavior silently dropped these)."""
        _mock_delete, mock_write = _run()
        mock_write.assert_called_once()
        written_row = mock_write.call_args[0][0]
        assert written_row["game_ce_id"] == GAME_ID
        assert written_row["status"] == "stable"
        assert "Doomed Game" in written_row["title"]
        assert "removed" in written_row["title"].lower()

    def test_deletes_before_announcing(self):
        """If the announcement write fails, we want that to be the rarer
        failure (a delete that already succeeded, followed immediately by
        a write failing) rather than deleting after announcing, which
        would mean a failed delete leaves the game still "removed" from
        Discord's perspective but still present in Supabase -- retried
        endlessly-but-safely next loop either way, but this ordering means
        a delete failure never produces a duplicate announcement."""
        call_order = []
        with (
            patch(
                "web_scraper.scraper.SupabaseReader.delete_game",
                side_effect=lambda ce_id: call_order.append("delete"),
            ),
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_update",
                side_effect=lambda row: call_order.append("write"),
            ),
        ):
            asyncio.run(
                announce_removed_game(make_game(ce_id=GAME_ID), send_updates=True)
            )
        assert call_order == ["delete", "write"]

    def test_send_updates_false_does_not_write_but_still_deletes(self):
        mock_delete, mock_write = _run(send_updates=False)
        mock_write.assert_not_called()
        mock_delete.assert_called_once_with(GAME_ID)

    def test_delete_failure_propagates_to_the_caller(self):
        """announce_removed_game itself does not catch delete errors --
        update_games's removed-games loop is responsible for isolating one
        game's failure from the rest of the batch."""
        with (
            patch(
                "web_scraper.scraper.SupabaseReader.delete_game",
                side_effect=RuntimeError("transient Supabase error"),
            ),
            patch("web_scraper.scraper.SupabaseReader.write_scraper_update"),
        ):
            try:
                asyncio.run(
                    announce_removed_game(make_game(ce_id=GAME_ID), send_updates=True)
                )
                raised = False
            except RuntimeError:
                raised = True
        assert raised

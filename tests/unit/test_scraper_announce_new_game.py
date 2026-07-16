import asyncio
from unittest.mock import AsyncMock, patch

from tests.conftest import make_api_game
from web_scraper.scraper import announce_new_game

GAME_ID = "game-001-0000-0000-000000000000"


def _run(current_api_game, send_updates: bool = True, notIsFinished: set | None = None):
    if notIsFinished is None:
        notIsFinished = set()
    with (
        patch(
            "web_scraper.scraper.CEAPIReader.get_game",
            new_callable=AsyncMock,
            return_value=current_api_game,
        ) as mock_get_game,
        patch("web_scraper.scraper.SupabaseReader.write_scraper_update") as mock_write,
        patch("web_scraper.scraper.SupabaseReader.bulk_dump_games") as mock_dump,
    ):
        asyncio.run(
            announce_new_game(make_api_game(ce_id=GAME_ID), notIsFinished, send_updates)
        )
    return mock_get_game, mock_write, mock_dump, notIsFinished


class TestAnnounceNewGame:
    def test_re_fetches_by_id_instead_of_using_detection_payload(self):
        """The message must be built from a fresh /api/game/{id} fetch (which
        always has gameTags), not from whatever payload first detected the
        game -- that payload may have come from the daily full_scrape hit
        (/api/games/full), which omits gameTags entirely."""
        fresh_game = make_api_game(
            ce_id=GAME_ID,
            game_tags=[
                {"tagId": "t1", "tag": {"name": "Tower Defense", "type": "genre"}}
            ],
        )
        mock_get_game, mock_write, _mock_dump, _notf = _run(fresh_game)

        mock_get_game.assert_called_once_with(GAME_ID)
        mock_write.assert_called_once()
        written_row = mock_write.call_args[0][0]
        assert written_row["game_ce_id"] == GAME_ID
        assert written_row["status"] == "stable"
        assert "Genre tags: Tower Defense" in written_row["description"]

    def test_vanished_game_writes_and_persists_nothing(self):
        """Re-fetch returns None (game removed between detection and
        announcement) -- drop it, don't crash, don't persist a game that
        doesn't exist."""
        _mock_get_game, mock_write, mock_dump, notf = _run(None)
        mock_write.assert_not_called()
        mock_dump.assert_not_called()
        assert notf == set()

    def test_hidden_game_writes_nothing_and_is_tracked_as_not_finished(self):
        """Game exists but isn't finished/published -- don't announce or
        persist it as a normal game, but do track it in notIsFinished (like
        every other hidden game in update_games) so it's picked back up and
        properly announced once it's actually published."""
        hidden_game = make_api_game(ce_id=GAME_ID, is_finished=False)
        _mock_get_game, mock_write, mock_dump, notf = _run(hidden_game)
        mock_write.assert_not_called()
        mock_dump.assert_not_called()
        assert notf == {GAME_ID}

    def test_writes_directly_as_stable_not_pending(self):
        """New-game announcements bypass the pending/stabilize debounce
        entirely -- they're written straight to stable."""
        _mock_get_game, mock_write, _mock_dump, _notf = _run(
            make_api_game(ce_id=GAME_ID)
        )
        written_row = mock_write.call_args[0][0]
        assert written_row["status"] == "stable"

    def test_persists_the_game_immediately(self):
        """Persisting here (rather than leaving it to the caller's later
        batched dump) closes the window where a later failure elsewhere in
        the loop would leave the game looking "new" again next loop and
        cause a duplicate announcement."""
        fresh_game = make_api_game(ce_id=GAME_ID)
        _mock_get_game, _mock_write, mock_dump, _notf = _run(fresh_game)
        mock_dump.assert_called_once_with([fresh_game])

    def test_propagates_fetch_failures_to_the_caller(self):
        """announce_new_game itself does not catch errors from the live CE
        API call -- update_games's per-game loop is responsible for
        isolating one game's failure from the rest of the batch."""
        with (
            patch(
                "web_scraper.scraper.CEAPIReader.get_game",
                new_callable=AsyncMock,
                side_effect=RuntimeError("transient CE API error"),
            ),
            patch("web_scraper.scraper.SupabaseReader.write_scraper_update"),
            patch("web_scraper.scraper.SupabaseReader.bulk_dump_games"),
        ):
            try:
                asyncio.run(
                    announce_new_game(make_api_game(ce_id=GAME_ID), set(), True)
                )
                raised = False
            except RuntimeError:
                raised = True
        assert raised

    def test_send_updates_false_does_not_write_but_still_persists(self):
        """Mirrors process_loop's silent/recovery-scrape contract: no
        message gets sent, but the game's data still gets persisted --
        data sync is independent of whether announcements go out."""
        fresh_game = make_api_game(ce_id=GAME_ID)
        _mock_get_game, mock_write, mock_dump, _notf = _run(
            fresh_game, send_updates=False
        )
        mock_write.assert_not_called()
        mock_dump.assert_called_once_with([fresh_game])

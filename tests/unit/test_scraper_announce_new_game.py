import asyncio
from unittest.mock import AsyncMock, patch

from tests.conftest import make_api_game
from web_scraper.scraper import announce_new_game

GAME_ID = "game-001-0000-0000-000000000000"


def _run(current_api_game) -> None:
    with (
        patch(
            "web_scraper.scraper.CEAPIReader.get_game",
            new_callable=AsyncMock,
            return_value=current_api_game,
        ) as mock_get_game,
        patch("web_scraper.scraper.SupabaseReader.write_scraper_update") as mock_write,
    ):
        asyncio.run(announce_new_game(make_api_game(ce_id=GAME_ID)))
    return mock_get_game, mock_write


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
        mock_get_game, mock_write = _run(fresh_game)

        mock_get_game.assert_called_once_with(GAME_ID)
        mock_write.assert_called_once()
        written_row = mock_write.call_args[0][0]
        assert written_row["game_ce_id"] == GAME_ID
        assert written_row["status"] == "stable"
        assert "Genre tags: Tower Defense" in written_row["description"]

    def test_vanished_game_writes_nothing(self):
        """Re-fetch returns None (game removed between detection and
        announcement) -- drop it, don't crash."""
        _mock_get_game, mock_write = _run(None)
        mock_write.assert_not_called()

    def test_hidden_game_writes_nothing(self):
        """Game exists but isn't finished/published -- don't announce it."""
        hidden_game = make_api_game(ce_id=GAME_ID, is_finished=False)
        _mock_get_game, mock_write = _run(hidden_game)
        mock_write.assert_not_called()

    def test_writes_directly_as_stable_not_pending(self):
        """New-game announcements bypass the pending/stabilize debounce
        entirely -- they're written straight to stable."""
        _mock_get_game, mock_write = _run(make_api_game(ce_id=GAME_ID))
        written_row = mock_write.call_args[0][0]
        assert written_row["status"] == "stable"

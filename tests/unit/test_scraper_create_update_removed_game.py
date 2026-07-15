from tests.conftest import make_game
from web_scraper.scraper import (
    UpdateMessageForScraperProcess,
    create_update_removed_game,
)

GAME_ID = "game-001-0000-0000-000000000000"


class TestCreateUpdateRemovedGame:
    def test_returns_update_message(self):
        game = make_game(ce_id=GAME_ID, game_name="Removed Game")
        update = create_update_removed_game(game)
        assert isinstance(update, UpdateMessageForScraperProcess)

    def test_is_embed(self):
        update = create_update_removed_game(make_game(ce_id=GAME_ID))
        assert update.is_embed is True

    def test_title_mentions_game_name(self):
        update = create_update_removed_game(
            make_game(ce_id=GAME_ID, game_name="Vanishing Game")
        )
        assert "Vanishing Game" in update.title
        assert "removed" in update.title.lower()

    def test_location_is_gameadditions(self):
        update = create_update_removed_game(make_game(ce_id=GAME_ID))
        assert update.location == "gameadditions"

    def test_game_ce_id_is_set(self):
        update = create_update_removed_game(make_game(ce_id=GAME_ID))
        assert update.game_ce_id == GAME_ID

from tests.conftest import make_api_game, make_game
from web_scraper.scraper import (
    UpdateMessageForScraperProcess,
    create_update_removed_game,
    update_one_game,
)

GAME_ID = "game-001-0000-0000-000000000000"


# ── create_update_removed_game ──────────────────────────────────────────────────


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


# ── update_one_game ──────────────────────────────────────────────────────────────
# New games are handled separately by announce_new_game (see
# test_scraper_announce_new_game.py) -- update_one_game only ever deals with
# an existing game being removed or updated.


class TestUpdateOneGameRemovedGame:
    def test_returns_removed_game_update(self):
        old_game = make_game(ce_id=GAME_ID, game_name="Doomed Game")
        update, _removed = update_one_game(old_game, None)
        assert update is not None
        assert "Doomed Game" in update.title
        assert "removed" in update.title.lower()

    def test_removed_objective_ids_is_empty_list(self):
        old_game = make_game(ce_id=GAME_ID)
        _, removed = update_one_game(old_game, None)
        assert removed == []


class TestUpdateOneGameUpdatedGame:
    def test_dispatches_to_updated_game_when_both_present(self):
        old_game = make_game(ce_id=GAME_ID, game_name="Same Game")
        new_game = make_api_game(ce_id=GAME_ID, game_name="Same Game")
        update, removed = update_one_game(old_game, new_game)
        # identical games produce no update, matching create_update_updated_game's
        # no-op behavior for unchanged data.
        assert update is None
        assert removed is None

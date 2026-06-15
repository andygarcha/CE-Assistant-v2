from Modules.CEAPIReader import _ce_to_game


def _minimal_api_response(**overrides) -> dict:
    response = {
        "id": "game-001-0000-0000-000000000000",
        "name": "Test Game",
        "platform": "PC",
        "platformId": "12345",
        "header": "https://example.com/header.png",
        "updatedAt": "2024-02-25T07:04:38.000Z",
        "genre": {"name": "Action"},
        "gameCategories": [],
        "objectives": [],
    }
    response.update(overrides)
    return response


def test_ce_to_game_uses_genre_fallback_as_list_of_categories():
    """When `gameCategories` is empty, categories should fall back to the
    game's genre name as a single-element list, not the bare string."""
    game = _ce_to_game(_minimal_api_response())

    assert game is not None
    assert game.categories == ["Action"]

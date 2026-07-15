from Classes.CE_Objective import CEObjective
from tests.conftest import make_api_game, make_game_tag, make_objective
from web_scraper.scraper import create_update_new_game


def _po(points: int, name: str = "Test PO") -> CEObjective:
    return make_objective(point_value=points, obj_type="Primary", name=name)


def _uncleared_po() -> CEObjective:
    return make_objective(
        point_value=0, obj_type="Primary", name="Uncleared PO (UNCLEARED)"
    )


def _so(points: int, name: str = "Test SO") -> CEObjective:
    return make_objective(point_value=points, obj_type="Secondary", name=name)


def _uncleared_so() -> CEObjective:
    return make_objective(
        point_value=0, obj_type="Secondary", name="Uncleared SO (UNCLEARED)"
    )


def _co() -> CEObjective:
    return make_objective(point_value=0, obj_type="Community", name="Test CO")


class TestCreateUpdateNewGameStructure:
    """Tests for fields that are always set regardless of objective composition."""

    def test_returns_embed(self):
        update = create_update_new_game(make_api_game())
        assert update.is_embed is True

    def test_location_is_gameadditions(self):
        update = create_update_new_game(make_api_game())
        assert update.location == "gameadditions"

    def test_color_is_green(self):
        update = create_update_new_game(make_api_game())
        assert update.color == 0x48B474

    def test_title_contains_game_name(self):
        update = create_update_new_game(make_api_game(game_name="Portal 2"))
        assert "Portal 2" in update.title

    def test_title_says_added_to_site(self):
        update = create_update_new_game(make_api_game(game_name="Portal 2"))
        assert "added to the site" in update.title

    def test_url_uses_ce_id(self):
        update = create_update_new_game(make_api_game(ce_id="aaaa-1111-bbbb-2222"))
        assert update.url == "https://cedb.me/game/aaaa-1111-bbbb-2222"

    def test_description_contains_emojis(self):
        game = make_api_game(categories=["Action"])
        update = create_update_new_game(game)
        assert game.emojis in update.description

    def test_description_emojis_line_is_bullet(self):
        update = create_update_new_game(make_api_game())
        assert "\n-" in update.description


class TestCreateUpdateNewGameObjectiveSummary:
    """
    Tests for the objective-summary lines shown in the docstring:

        - 3 Primary Objectives worth 25 points (+2 Uncleareds)
        - 5 Secondary Objectives worth 100 points (+1 Uncleared)
        - 1 Community Objective
    """

    def test_primary_objective_count_in_description(self):
        game = make_api_game(objectives=[_po(10), _po(15)])
        update = create_update_new_game(game)
        assert "2 Primary" in update.description

    def test_primary_objective_points_in_description(self):
        game = make_api_game(objectives=[_po(10), _po(15)])
        update = create_update_new_game(game)
        assert "25" in update.description

    def test_primary_uncleared_count_in_description(self):
        game = make_api_game(objectives=[_po(10), _uncleared_po(), _uncleared_po()])
        update = create_update_new_game(game)
        assert "+2" in update.description

    def test_no_uncleared_mention_when_none(self):
        game = make_api_game(objectives=[_po(10), _po(20)])
        update = create_update_new_game(game)
        # No uncleared POs → the "(+N Uncleared)" suffix should not appear
        assert "(+" not in update.description

    def test_secondary_objective_count_in_description(self):
        game = make_api_game(objectives=[_so(50), _so(50), _so(50)])
        update = create_update_new_game(game)
        assert "3 Secondary" in update.description

    def test_secondary_objective_points_in_description(self):
        game = make_api_game(objectives=[_so(40), _so(60)])
        update = create_update_new_game(game)
        assert "100" in update.description

    def test_secondary_uncleared_count_in_description(self):
        game = make_api_game(objectives=[_so(50), _uncleared_so()])
        update = create_update_new_game(game)
        assert "+1" in update.description

    def test_community_objective_count_in_description(self):
        game = make_api_game(objectives=[_co()])
        update = create_update_new_game(game)
        assert "1 Community" in update.description

    def test_multiple_community_objectives_in_description(self):
        game = make_api_game(objectives=[_co(), _co(), _co()])
        update = create_update_new_game(game)
        assert "3 Community" in update.description

    def test_no_primary_line_when_no_primary_objectives(self):
        game = make_api_game(objectives=[_so(50)])
        update = create_update_new_game(game)
        assert "Primary" not in update.description

    def test_no_secondary_line_when_no_secondary_objectives(self):
        game = make_api_game(objectives=[_po(10)])
        update = create_update_new_game(game)
        assert "Secondary" not in update.description

    def test_no_community_line_when_no_community_objectives(self):
        game = make_api_game(objectives=[_po(10)])
        update = create_update_new_game(game)
        assert "Community" not in update.description

    def test_all_objective_types_appear_together(self):
        game = make_api_game(
            objectives=[_po(10), _po(15), _so(50), _uncleared_so(), _co()]
        )
        update = create_update_new_game(game)
        assert "Primary" in update.description
        assert "Secondary" in update.description
        assert "Community" in update.description


def _genre_tag(name: str) -> dict:
    return make_game_tag(name, "genre")


def _info_tag(name: str) -> dict:
    return make_game_tag(name, "informational")


class TestCreateUpdateNewGameTags:
    """
    Tests for the genre/informational tag lines shown in the docstring:

        - Genre tags: Tower Defense, Traditional Fighter (+3 more)
        - Informational tags: Animal Protagonist, Curated (+18 more)
    """

    def test_no_genre_tags_line_when_no_genre_tags(self):
        game = make_api_game(game_tags=[])
        update = create_update_new_game(game)
        assert "Genre tags" not in update.description

    def test_no_informational_tags_line_when_no_informational_tags(self):
        game = make_api_game(game_tags=[])
        update = create_update_new_game(game)
        assert "Informational tags" not in update.description

    def test_genre_tags_line_shown_when_present(self):
        game = make_api_game(game_tags=[_genre_tag("Tower Defense")])
        update = create_update_new_game(game)
        assert "Genre tags:" in update.description

    def test_genre_tags_line_is_bullet(self):
        game = make_api_game(game_tags=[_genre_tag("Tower Defense")])
        update = create_update_new_game(game)
        assert "\n- Genre tags:" in update.description

    def test_genre_tag_names_appear_in_description(self):
        game = make_api_game(
            game_tags=[_genre_tag("Tower Defense"), _genre_tag("Traditional Fighter")]
        )
        update = create_update_new_game(game)
        assert "Tower Defense" in update.description
        assert "Traditional Fighter" in update.description

    def test_genre_tags_no_more_suffix_when_two_or_fewer(self):
        game = make_api_game(
            game_tags=[_genre_tag("Tower Defense"), _genre_tag("Traditional Fighter")]
        )
        update = create_update_new_game(game)
        assert "more" not in update.description

    def test_genre_tags_more_suffix_matches_remaining_count(self):
        game = make_api_game(
            game_tags=[
                _genre_tag("Tower Defense"),
                _genre_tag("Traditional Fighter"),
                _genre_tag("Roguelike"),
                _genre_tag("Metroidvania"),
                _genre_tag("Puzzle"),
            ]
        )
        update = create_update_new_game(game)
        assert "(+3 more)" in update.description

    def test_informational_tags_line_shown_when_present(self):
        game = make_api_game(game_tags=[_info_tag("Curated")])
        update = create_update_new_game(game)
        assert "Informational tags:" in update.description

    def test_informational_tags_line_is_bullet(self):
        game = make_api_game(game_tags=[_info_tag("Curated")])
        update = create_update_new_game(game)
        assert "\n- Informational tags:" in update.description

    def test_informational_tag_names_appear_in_description(self):
        game = make_api_game(
            game_tags=[_info_tag("Animal Protagonist"), _info_tag("Curated")]
        )
        update = create_update_new_game(game)
        assert "Animal Protagonist" in update.description
        assert "Curated" in update.description

    def test_informational_tags_no_more_suffix_when_two_or_fewer(self):
        game = make_api_game(
            game_tags=[_info_tag("Animal Protagonist"), _info_tag("Curated")]
        )
        update = create_update_new_game(game)
        assert "more" not in update.description

    def test_informational_tags_more_suffix_matches_remaining_count(self):
        game = make_api_game(
            game_tags=[_info_tag(f"Tag {i}") for i in range(20)],
        )
        update = create_update_new_game(game)
        assert "(+18 more)" in update.description

    def test_genre_and_informational_tags_appear_together(self):
        game = make_api_game(
            game_tags=[
                _genre_tag("Tower Defense"),
                _info_tag("Curated"),
            ]
        )
        update = create_update_new_game(game)
        assert "Genre tags:" in update.description
        assert "Informational tags:" in update.description

    def test_genre_tags_do_not_leak_into_informational_line(self):
        game = make_api_game(game_tags=[_genre_tag("Tower Defense")])
        update = create_update_new_game(game)
        assert "Informational tags" not in update.description

    def test_informational_tags_do_not_leak_into_genre_line(self):
        game = make_api_game(game_tags=[_info_tag("Curated")])
        update = create_update_new_game(game)
        assert "Genre tags" not in update.description

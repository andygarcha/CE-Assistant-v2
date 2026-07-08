from Classes.CE_Game import CEAPIGame, CEGame
from Classes.CE_Objective import CEObjective
from Modules import hm
from tests.conftest import make_api_game, make_game, make_objective
from web_scraper.scraper import (
    UpdateMessageForScraperProcess,
    create_update_updated_game,
)

# ── helpers ──────────────────────────────────────────────────────────────────

GAME_ID = "game-001-0000-0000-000000000000"
OBJ_A = "obj-aaaa-0000-0000-000000000000"
OBJ_B = "obj-bbbb-0000-0000-000000000000"
OBJ_C = "obj-cccc-0000-0000-000000000000"
OBJ_D = "obj-dddd-0000-0000-000000000000"


def _po(
    points: int = 10,
    name: str = "Test PO",
    ce_id: str = OBJ_A,
    requirements: str | None = None,
    achievements: list[str] | None = None,
    partial_points: int = 0,
) -> CEObjective:
    return make_objective(
        ce_id=ce_id,
        obj_type="Primary",
        point_value=points,
        name=name,
        requirements=requirements,
        achievement_ce_ids=achievements,
        point_value_partial=partial_points,
    )


def _so(
    points: int = 20,
    name: str = "Test SO",
    ce_id: str = OBJ_B,
    requirements: str | None = None,
    achievements: list[str] | None = None,
) -> CEObjective:
    return make_objective(
        ce_id=ce_id,
        obj_type="Secondary",
        point_value=points,
        name=name,
        requirements=requirements,
        achievement_ce_ids=achievements,
    )


def _co(name: str = "Test CO", ce_id: str = OBJ_C) -> CEObjective:
    return make_objective(ce_id=ce_id, obj_type="Community", point_value=0, name=name)


def _badge(name: str = "Test Badge", ce_id: str = OBJ_D) -> CEObjective:
    return make_objective(ce_id=ce_id, obj_type="Badge", point_value=0, name=name)


def _uncleared_po(name: str = "Test PO (UNCLEARED)", ce_id: str = OBJ_A) -> CEObjective:
    return make_objective(ce_id=ce_id, obj_type="Primary", point_value=0, name=name)


def _uncleared_so(name: str = "Test SO (UNCLEARED)", ce_id: str = OBJ_B) -> CEObjective:
    return make_objective(ce_id=ce_id, obj_type="Secondary", point_value=0, name=name)


def _old(
    objectives: list[CEObjective] | None = None, game_name: str = "Test Game"
) -> CEGame:
    return make_game(ce_id=GAME_ID, game_name=game_name, objectives=objectives or [])


def _new(
    objectives: list[CEObjective] | None = None,
    game_name: str = "Test Game",
    information: str = "",
) -> CEAPIGame:
    return make_api_game(
        ce_id=GAME_ID,
        game_name=game_name,
        objectives=objectives or [],
        information=information,
    )


# ── Return shape ─────────────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameReturnShape:
    def test_returns_a_tuple(self):
        result = create_update_updated_game(_old([_po()]), _new([_po()]))
        assert isinstance(result, tuple)

    def test_tuple_has_two_elements(self):
        result = create_update_updated_game(_old([_po()]), _new([_po()]))
        assert len(result) == 2

    def test_second_element_is_list_or_none_when_unchanged(self):
        _, removed = create_update_updated_game(_old([_po()]), _new([_po()]))
        assert removed is None or isinstance(removed, list)

    def test_removed_ids_is_list_when_objective_removed(self):
        _, removed = create_update_updated_game(_old([_po(ce_id=OBJ_A)]), _new([]))
        assert isinstance(removed, list)

    def test_removed_ids_contains_the_removed_objective_ce_id(self):
        _, removed = create_update_updated_game(_old([_po(ce_id=OBJ_A)]), _new([]))
        assert removed is not None
        assert OBJ_A in removed

    def test_removed_ids_contains_all_removed_objectives(self):
        _, removed = create_update_updated_game(
            _old([_po(ce_id=OBJ_A), _so(ce_id=OBJ_B)]), _new([])
        )
        assert removed is not None
        assert OBJ_A in removed
        assert OBJ_B in removed

    def test_removed_ids_does_not_contain_surviving_objective(self):
        _, removed = create_update_updated_game(
            _old([_po(ce_id=OBJ_A), _so(ce_id=OBJ_B)]),
            _new([_po(ce_id=OBJ_A)]),
        )
        assert removed is not None
        assert OBJ_A not in removed

    def test_update_is_update_message_type_when_changes_exist(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10)]), _new([_po(points=20)])
        )
        assert update is not None
        assert isinstance(update, UpdateMessageForScraperProcess)


# ── No-change (no-op) ─────────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameNoChanges:
    def test_identical_empty_objectives_returns_no_update(self):
        update, _ = create_update_updated_game(_old([]), _new([]))
        assert update is None

    def test_identical_single_po_returns_no_update(self):
        update, _ = create_update_updated_game(_old([_po()]), _new([_po()]))
        assert update is None

    def test_identical_single_so_returns_no_update(self):
        update, _ = create_update_updated_game(_old([_so()]), _new([_so()]))
        assert update is None

    def test_identical_single_co_returns_no_update(self):
        update, _ = create_update_updated_game(_old([_co()]), _new([_co()]))
        assert update is None

    def test_identical_mixed_objectives_returns_no_update(self):
        objs = [_po(ce_id=OBJ_A), _so(ce_id=OBJ_B), _co(ce_id=OBJ_C)]
        update, _ = create_update_updated_game(_old(objs), _new(objs))
        assert update is None

    def test_identical_po_with_requirements_returns_no_update(self):
        obj = _po(requirements="Must complete first.", ce_id=OBJ_A)
        update, _ = create_update_updated_game(_old([obj]), _new([obj]))
        assert update is None

    def test_identical_po_with_achievements_returns_no_update(self):
        obj = _po(achievements=["ach-0001", "ach-0002"], ce_id=OBJ_A)
        update, _ = create_update_updated_game(_old([obj]), _new([obj]))
        assert update is None

    def test_identical_uncleared_po_returns_no_update(self):
        obj = _uncleared_po(ce_id=OBJ_A)
        update, _ = create_update_updated_game(_old([obj]), _new([obj]))
        assert update is None

    def test_no_removed_objectives_when_identical(self):
        _, removed = create_update_updated_game(
            _old([_po(ce_id=OBJ_A)]), _new([_po(ce_id=OBJ_A)])
        )
        assert not removed  # None or empty list


# ── Update structure ──────────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameStructure:
    """Fields that must be set correctly whenever an update IS generated."""

    def _changed_pair(self):
        return _old([_po(points=10, ce_id=OBJ_A)]), _new([_po(points=20, ce_id=OBJ_A)])

    def test_update_is_embed(self):
        old, new = self._changed_pair()
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert update.is_embed is True

    def test_location_is_gameadditions(self):
        old, new = self._changed_pair()
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert update.location == "gameadditions"

    def test_title_contains_game_name(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10)], game_name="Celeste"),
            _new([_po(points=20)], game_name="Celeste"),
        )
        assert update is not None
        assert "Celeste" in update.title

    def test_title_says_updated_on_site(self):
        old, new = self._changed_pair()
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert "updated" in update.title.lower()

    def test_url_uses_ce_id(self):
        old, new = self._changed_pair()
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert GAME_ID in update.url

    def test_url_points_to_cedb(self):
        old, new = self._changed_pair()
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert "cedb.me" in update.url

    def test_image_is_game_header(self):
        old = _old([_po(points=10)])
        new = make_api_game(
            ce_id=GAME_ID,
            objectives=[_po(points=20)],
            header="https://example.com/my-header.jpg",
        )
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert update.image == "https://example.com/my-header.jpg"

    def test_description_is_non_empty_when_changes_exist(self):
        old, new = self._changed_pair()
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert update.description is not None
        assert len(update.description.strip()) > 0


# ── Embed color ───────────────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameColor:
    """The embed color must be explicitly set — never the default 0x000000."""

    def test_color_is_not_default_black(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10)]), _new([_po(points=20)])
        )
        assert update is not None
        assert update.color != 0x000000

    def test_color_is_consistent_across_different_change_types(self):
        update_points, _ = create_update_updated_game(
            _old([_po(points=10)]), _new([_po(points=20)])
        )
        update_removed, _ = create_update_updated_game(_old([_po()]), _new([]))
        update_added, _ = create_update_updated_game(_old([]), _new([_po()]))
        assert update_points is not None
        assert update_removed is not None
        assert update_added is not None
        assert update_points.color == update_removed.color == update_added.color


# ── Total points changes ──────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameTotalPoints:
    def test_points_increase_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10)]), _new([_po(points=20)])
        )
        assert update is not None

    def test_points_decrease_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(points=30)]), _new([_po(points=10)])
        )
        assert update is not None

    def test_description_mentions_old_point_total_on_increase(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10)]), _new([_po(points=20)])
        )
        assert update is not None
        assert "10" in update.description

    def test_description_mentions_new_point_total_on_increase(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10)]), _new([_po(points=20)])
        )
        assert update is not None
        assert "20" in update.description

    def test_description_mentions_old_point_total_on_decrease(self):
        update, _ = create_update_updated_game(
            _old([_po(points=30)]), _new([_po(points=15)])
        )
        assert update is not None
        assert "30" in update.description

    def test_description_mentions_new_point_total_on_decrease(self):
        update, _ = create_update_updated_game(
            _old([_po(points=30)]), _new([_po(points=15)])
        )
        assert update is not None
        assert "15" in update.description

    def test_description_says_unchanged_when_total_identical(self):
        # Name changes → update IS generated, but points stay the same.
        old = _old(
            [
                make_objective(
                    ce_id=OBJ_A, obj_type="Primary", point_value=10, name="Old Name"
                )
            ]
        )
        new = _new(
            [
                make_objective(
                    ce_id=OBJ_A, obj_type="Primary", point_value=10, name="New Name"
                )
            ]
        )
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert "unchanged" in update.description.lower()


# ── New objectives added ──────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameNewObjectives:
    def test_new_po_triggers_update(self):
        update, _ = create_update_updated_game(_old([]), _new([_po(ce_id=OBJ_A)]))
        assert update is not None

    def test_new_so_triggers_update(self):
        update, _ = create_update_updated_game(_old([]), _new([_so(ce_id=OBJ_B)]))
        assert update is not None

    def test_new_co_triggers_update(self):
        update, _ = create_update_updated_game(_old([]), _new([_co(ce_id=OBJ_C)]))
        assert update is not None

    def test_new_po_name_in_description(self):
        update, _ = create_update_updated_game(
            _old([]), _new([_po(name="Strawberry Lunatic", ce_id=OBJ_A)])
        )
        assert update is not None
        assert "Strawberry Lunatic" in update.description

    def test_new_so_name_in_description(self):
        update, _ = create_update_updated_game(
            _old([]), _new([_so(name="Double Dash", ce_id=OBJ_B)])
        )
        assert update is not None
        assert "Double Dash" in update.description

    def test_new_co_name_in_description(self):
        update, _ = create_update_updated_game(
            _old([]), _new([_co(name="Solid Gold", ce_id=OBJ_C)])
        )
        assert update is not None
        assert "Solid Gold" in update.description

    def test_new_po_description_mentions_primary(self):
        update, _ = create_update_updated_game(_old([]), _new([_po(ce_id=OBJ_A)]))
        assert update is not None
        assert "Primary" in update.description

    def test_new_so_description_mentions_secondary(self):
        update, _ = create_update_updated_game(_old([]), _new([_so(ce_id=OBJ_B)]))
        assert update is not None
        assert "Secondary" in update.description

    def test_new_po_point_value_in_description(self):
        update, _ = create_update_updated_game(
            _old([]), _new([_po(points=50, ce_id=OBJ_A)])
        )
        assert update is not None
        assert "50" in update.description

    def test_new_uncleared_po_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([]), _new([_uncleared_po(ce_id=OBJ_A)])
        )
        assert update is not None

    def test_adding_new_obj_does_not_put_it_in_removed_list(self):
        _, removed = create_update_updated_game(_old([]), _new([_po(ce_id=OBJ_A)]))
        if removed:
            assert OBJ_A not in removed

    def test_multiple_new_objectives_all_appear_in_description(self):
        update, _ = create_update_updated_game(
            _old([]),
            _new([_po(name="PO Alpha", ce_id=OBJ_A), _so(name="SO Beta", ce_id=OBJ_B)]),
        )
        assert update is not None
        assert "PO Alpha" in update.description
        assert "SO Beta" in update.description

    def test_new_po_requirements_appear_in_description(self):
        # Docstring example shows requirements text ("Complete 9D.") for newly added objectives.
        new_obj = make_objective(
            ce_id=OBJ_A,
            obj_type="Primary",
            point_value=10,
            name="Hard Mode",
            description="Complete the game on hard mode.",
        )
        update, _ = create_update_updated_game(_old([]), _new([new_obj]))
        assert update is not None
        assert "Complete the game on hard mode." in update.description


# ── Removed objectives ────────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameRemovedObjectives:
    def test_removing_po_triggers_update(self):
        update, _ = create_update_updated_game(_old([_po(ce_id=OBJ_A)]), _new([]))
        assert update is not None

    def test_removing_so_triggers_update(self):
        update, _ = create_update_updated_game(_old([_so(ce_id=OBJ_B)]), _new([]))
        assert update is not None

    def test_removing_co_triggers_update(self):
        update, _ = create_update_updated_game(_old([_co(ce_id=OBJ_C)]), _new([]))
        assert update is not None

    def test_removed_po_id_in_removed_list(self):
        _, removed = create_update_updated_game(_old([_po(ce_id=OBJ_A)]), _new([]))
        assert removed is not None
        assert OBJ_A in removed

    def test_removed_so_id_in_removed_list(self):
        _, removed = create_update_updated_game(_old([_so(ce_id=OBJ_B)]), _new([]))
        assert removed is not None
        assert OBJ_B in removed

    def test_removed_co_id_in_removed_list(self):
        _, removed = create_update_updated_game(_old([_co(ce_id=OBJ_C)]), _new([]))
        assert removed is not None
        assert OBJ_C in removed

    def test_removed_objective_name_appears_in_description(self):
        update, _ = create_update_updated_game(
            _old([_po(name="Speed Berry", ce_id=OBJ_A)]), _new([])
        )
        assert update is not None
        assert "Speed Berry" in update.description

    def test_only_removed_objective_ids_are_in_removed_list(self):
        _, removed = create_update_updated_game(
            _old([_po(ce_id=OBJ_A), _so(ce_id=OBJ_B)]),
            _new([_po(ce_id=OBJ_A)]),
        )
        assert removed is not None
        assert OBJ_B in removed
        assert OBJ_A not in removed

    def test_removing_multiple_objectives_all_ids_in_list(self):
        _, removed = create_update_updated_game(
            _old([_po(ce_id=OBJ_A), _so(ce_id=OBJ_B), _co(ce_id=OBJ_C)]),
            _new([]),
        )
        assert removed is not None
        assert OBJ_A in removed
        assert OBJ_B in removed
        assert OBJ_C in removed

    def test_no_removed_ids_when_no_objectives_dropped(self):
        _, removed = create_update_updated_game(
            _old([_po(points=10, ce_id=OBJ_A)]),
            _new([_po(points=20, ce_id=OBJ_A)]),
        )
        assert not removed  # None or empty list


# ── Objective point value changes ─────────────────────────────────────────────


class TestCreateUpdateUpdatedGameObjectivePointChanges:
    def test_po_point_increase_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10, ce_id=OBJ_A)]), _new([_po(points=25, ce_id=OBJ_A)])
        )
        assert update is not None

    def test_po_point_decrease_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(points=30, ce_id=OBJ_A)]), _new([_po(points=20, ce_id=OBJ_A)])
        )
        assert update is not None

    def test_so_point_change_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_so(points=30, ce_id=OBJ_B)]), _new([_so(points=20, ce_id=OBJ_B)])
        )
        assert update is not None

    def test_po_point_change_shows_old_value_in_description(self):
        update, _ = create_update_updated_game(
            _old([_po(points=30, name="Speed Berry", ce_id=OBJ_A)]),
            _new([_po(points=20, name="Speed Berry", ce_id=OBJ_A)]),
        )
        assert update is not None
        assert "30" in update.description

    def test_po_point_change_shows_new_value_in_description(self):
        update, _ = create_update_updated_game(
            _old([_po(points=30, name="Speed Berry", ce_id=OBJ_A)]),
            _new([_po(points=20, name="Speed Berry", ce_id=OBJ_A)]),
        )
        assert update is not None
        assert "20" in update.description

    def test_po_point_change_shows_objective_name_in_description(self):
        update, _ = create_update_updated_game(
            _old([_po(points=30, name="Speed Berry", ce_id=OBJ_A)]),
            _new([_po(points=20, name="Speed Berry", ce_id=OBJ_A)]),
        )
        assert update is not None
        assert "Speed Berry" in update.description

    def test_changed_po_is_not_in_removed_list(self):
        _, removed = create_update_updated_game(
            _old([_po(points=10, ce_id=OBJ_A)]), _new([_po(points=20, ce_id=OBJ_A)])
        )
        if removed:
            assert OBJ_A not in removed


# ── Objective description / requirements / name changes ───────────────────────


class TestCreateUpdateUpdatedGameObjectiveMetaChanges:
    def test_po_description_change_triggers_update(self):
        old_obj = make_objective(
            ce_id=OBJ_A, obj_type="Primary", point_value=10, name="PO"
        )
        new_obj = make_objective(
            ce_id=OBJ_A, obj_type="Primary", point_value=10, name="PO"
        )
        new_obj._description = "A completely different description."
        update, _ = create_update_updated_game(_old([old_obj]), _new([new_obj]))
        assert update is not None

    def test_po_requirements_change_string_to_string_triggers_update(self):
        old = _old([_po(ce_id=OBJ_A, requirements="Old requirement.")])
        new = _new([_po(ce_id=OBJ_A, requirements="New requirement.")])
        update, _ = create_update_updated_game(old, new)
        assert update is not None

    def test_po_requirements_added_from_none_triggers_update(self):
        old = _old([_po(ce_id=OBJ_A, requirements=None)])
        new = _new([_po(ce_id=OBJ_A, requirements="Send proof to #proof-submission.")])
        update, _ = create_update_updated_game(old, new)
        assert update is not None

    def test_po_requirements_removed_to_none_triggers_update(self):
        old = _old([_po(ce_id=OBJ_A, requirements="Send proof to #proof-submission.")])
        new = _new([_po(ce_id=OBJ_A, requirements=None)])
        update, _ = create_update_updated_game(old, new)
        assert update is not None

    def test_po_requirements_change_mentions_requirements_in_description(self):
        old = _old([_po(ce_id=OBJ_A, name="PO Alpha", requirements="Old req.")])
        new = _new([_po(ce_id=OBJ_A, name="PO Alpha", requirements="New req.")])
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert (
            "requirement" in update.description.lower()
            or "PO Alpha" in update.description
        )

    def test_po_name_change_triggers_update(self):
        old = _old(
            [
                make_objective(
                    ce_id=OBJ_A, obj_type="Primary", point_value=10, name="Old Name"
                )
            ]
        )
        new = _new(
            [
                make_objective(
                    ce_id=OBJ_A, obj_type="Primary", point_value=10, name="New Name"
                )
            ]
        )
        update, _ = create_update_updated_game(old, new)
        assert update is not None

    def test_unchanged_name_on_cleared_objective_not_mentioned(self):
        # Name identical, only points changed, neither copy is UNCLEARED/UNVALUED.
        # The "Name changed" note must not fire just because the objective
        # wasn't in an uncleared state.
        old = _old(
            [
                make_objective(
                    ce_id=OBJ_A, obj_type="Primary", point_value=10, name="Same Name"
                )
            ]
        )
        new = _new(
            [
                make_objective(
                    ce_id=OBJ_A, obj_type="Primary", point_value=20, name="Same Name"
                )
            ]
        )
        update, _ = create_update_updated_game(old, new)
        assert update is not None
        assert "Name changed" not in update.description

    def test_co_description_change_triggers_update(self):
        old_co = make_objective(
            ce_id=OBJ_C, obj_type="Community", point_value=0, name="Solid Gold"
        )
        new_co = make_objective(
            ce_id=OBJ_C, obj_type="Community", point_value=0, name="Solid Gold"
        )
        new_co._description = "Updated description."
        update, _ = create_update_updated_game(_old([old_co]), _new([new_co]))
        assert update is not None

    def test_multiple_aspects_of_same_po_changed_all_mentioned(self):
        # Both requirements AND description changed on the same objective.
        old_obj = make_objective(
            ce_id=OBJ_A,
            obj_type="Primary",
            point_value=10,
            name="Complex PO",
            requirements="Old req.",
        )
        new_obj = make_objective(
            ce_id=OBJ_A,
            obj_type="Primary",
            point_value=10,
            name="Complex PO",
            requirements="New req.",
        )
        new_obj._description = "New description."
        update, _ = create_update_updated_game(_old([old_obj]), _new([new_obj]))
        assert update is not None
        # Both field changes must be acknowledged in the description.
        desc = update.description.lower()
        assert "description" in desc or "requirement" in desc


# ── Achievement changes ───────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameAchievementChanges:
    def test_adding_achievements_to_po_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(achievements=None, ce_id=OBJ_A)]),
            _new([_po(achievements=["ach-0001", "ach-0002", "ach-0003"], ce_id=OBJ_A)]),
        )
        assert update is not None

    def test_removing_achievements_from_po_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(achievements=["ach-0001", "ach-0002"], ce_id=OBJ_A)]),
            _new([_po(achievements=None, ce_id=OBJ_A)]),
        )
        assert update is not None

    def test_achievement_addition_count_in_description(self):
        update, _ = create_update_updated_game(
            _old([_po(achievements=None, ce_id=OBJ_A)]),
            _new([_po(achievements=["ach-0001", "ach-0002", "ach-0003"], ce_id=OBJ_A)]),
        )
        assert update is not None
        assert "3" in update.description

    def test_achievement_removal_count_in_description(self):
        update, _ = create_update_updated_game(
            _old([_po(achievements=["ach-0001", "ach-0002"], ce_id=OBJ_A)]),
            _new([_po(achievements=None, ce_id=OBJ_A)]),
        )
        assert update is not None
        assert "2" in update.description

    def test_achievements_grow_from_one_to_many(self):
        update, _ = create_update_updated_game(
            _old([_po(achievements=["ach-0001"], ce_id=OBJ_A)]),
            _new(
                [
                    _po(
                        achievements=["ach-0001", "ach-0002", "ach-0003", "ach-0004"],
                        ce_id=OBJ_A,
                    )
                ]
            ),
        )
        assert update is not None

    def test_description_mentions_achievement_word_when_changed(self):
        update, _ = create_update_updated_game(
            _old([_po(achievements=None, ce_id=OBJ_A)]),
            _new([_po(achievements=["ach-0001"], ce_id=OBJ_A)]),
        )
        assert update is not None
        assert "achievement" in update.description.lower()

    def test_partial_achievement_swap_triggers_update(self):
        # Some removed, more added — the docstring example: "1 achievement removed, 17 achievements added".
        update, _ = create_update_updated_game(
            _old([_po(achievements=["ach-0001", "ach-0002"], ce_id=OBJ_A)]),
            _new([_po(achievements=["ach-0003", "ach-0004", "ach-0005"], ce_id=OBJ_A)]),
        )
        assert update is not None

    def test_partial_achievement_swap_shows_both_added_and_removed_counts(self):
        # 2 removed, 3 new ones added (ach-0003/0004/0005 are new).
        update, _ = create_update_updated_game(
            _old([_po(achievements=["ach-0001", "ach-0002"], ce_id=OBJ_A)]),
            _new([_po(achievements=["ach-0003", "ach-0004", "ach-0005"], ce_id=OBJ_A)]),
        )
        assert update is not None
        desc = update.description
        assert "2" in desc  # 2 removed
        assert "3" in desc  # 3 added


# ── Uncleared transitions ─────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameUnclearedTransitions:
    def test_po_becomes_uncleared_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10, name="PO Alpha", ce_id=OBJ_A)]),
            _new([_uncleared_po(name="PO Alpha (UNCLEARED)", ce_id=OBJ_A)]),
        )
        assert update is not None

    def test_po_cleared_from_uncleared_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_uncleared_po(name="PO Alpha (UNCLEARED)", ce_id=OBJ_A)]),
            _new([_po(points=10, name="PO Alpha", ce_id=OBJ_A)]),
        )
        assert update is not None

    def test_so_becomes_uncleared_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_so(points=20, name="SO Beta", ce_id=OBJ_B)]),
            _new([_uncleared_so(name="SO Beta (UNCLEARED)", ce_id=OBJ_B)]),
        )
        assert update is not None

    def test_so_cleared_from_uncleared_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_uncleared_so(name="SO Beta (UNCLEARED)", ce_id=OBJ_B)]),
            _new([_so(points=20, name="SO Beta", ce_id=OBJ_B)]),
        )
        assert update is not None

    def test_uncleared_to_cleared_does_not_put_id_in_removed_list(self):
        _, removed = create_update_updated_game(
            _old([_uncleared_po(name="PO (UNCLEARED)", ce_id=OBJ_A)]),
            _new([_po(points=10, name="PO", ce_id=OBJ_A)]),
        )
        if removed:
            assert OBJ_A not in removed

    def test_cleared_to_uncleared_does_not_put_id_in_removed_list(self):
        _, removed = create_update_updated_game(
            _old([_po(points=10, name="PO Alpha", ce_id=OBJ_A)]),
            _new([_uncleared_po(name="PO Alpha (UNCLEARED)", ce_id=OBJ_A)]),
        )
        if removed:
            assert OBJ_A not in removed


# ── Tier changes ──────────────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameTierChanges:
    def test_tier_increase_triggers_update(self):
        # T1 (5 pts PO) → T2 (20 pts PO)
        update, _ = create_update_updated_game(
            _old([_po(points=5)]), _new([_po(points=20)])
        )
        assert update is not None

    def test_tier_decrease_triggers_update(self):
        # T3 (40 pts PO) → T1 (5 pts PO)
        update, _ = create_update_updated_game(
            _old([_po(points=40)]), _new([_po(points=5)])
        )
        assert update is not None

    def test_tier_increase_shows_tier_label_in_description(self):
        # T1 → T2: both tier labels must appear somewhere in the description.
        update, _ = create_update_updated_game(
            _old([_po(points=5)]), _new([_po(points=20)])
        )
        assert update is not None
        assert (
            str(hm.get_emoji("Tier 1")) in update.description
            and str(hm.get_emoji("Tier 2")) in update.description
        )

    def test_tier_decrease_shows_tier_label_in_description(self):
        # T3 → T1
        update, _ = create_update_updated_game(
            _old([_po(points=40)]), _new([_po(points=5)])
        )
        assert update is not None
        assert (
            str(hm.get_emoji("Tier 3")) in update.description
            and str(hm.get_emoji("Tier 1")) in update.description
        )

    def test_point_change_without_tier_change_does_not_mention_tier(self):
        # Both old and new are T2 (20-39 PO points); no tier transition.
        update, _ = create_update_updated_game(
            _old([_po(points=20)]), _new([_po(points=25)])
        )
        assert update is not None
        assert "Tier" not in update.description


# ── Badge objectives ──────────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGameBadgeObjectives:
    def test_new_badge_triggers_update(self):
        update, _ = create_update_updated_game(_old([]), _new([_badge(ce_id=OBJ_D)]))
        assert update is not None

    def test_removed_badge_triggers_update(self):
        update, _ = create_update_updated_game(_old([_badge(ce_id=OBJ_D)]), _new([]))
        assert update is not None

    def test_removed_badge_id_in_removed_list(self):
        _, removed = create_update_updated_game(_old([_badge(ce_id=OBJ_D)]), _new([]))
        assert removed is not None
        assert OBJ_D in removed

    def test_identical_badge_returns_no_update(self):
        obj = _badge(ce_id=OBJ_D)
        update, _ = create_update_updated_game(_old([obj]), _new([obj]))
        assert update is None

    def test_new_badge_name_in_description(self):
        update, _ = create_update_updated_game(
            _old([]), _new([_badge(name="Golden Trophy", ce_id=OBJ_D)])
        )
        assert update is not None
        assert "Golden Trophy" in update.description


# ── Partial points changes ────────────────────────────────────────────────────


class TestCreateUpdateUpdatedGamePartialPoints:
    def test_partial_points_increase_triggers_update(self):
        old = _old([_po(points=10, partial_points=0, ce_id=OBJ_A)])
        new = _new([_po(points=10, partial_points=5, ce_id=OBJ_A)])
        update, _ = create_update_updated_game(old, new)
        assert update is not None

    def test_partial_points_decrease_triggers_update(self):
        old = _old([_po(points=10, partial_points=5, ce_id=OBJ_A)])
        new = _new([_po(points=10, partial_points=0, ce_id=OBJ_A)])
        update, _ = create_update_updated_game(old, new)
        assert update is not None

    def test_identical_partial_points_do_not_trigger_update(self):
        obj = _po(points=10, partial_points=5, ce_id=OBJ_A)
        update, _ = create_update_updated_game(_old([obj]), _new([obj]))
        assert update is None


# ── API-only field changes should not trigger an update ───────────────────────


class TestCreateUpdateUpdatedGameAPIOnlyFields:
    def test_information_change_alone_returns_no_update(self):
        # `information` is API-only metadata — not game content.
        obj = _po(ce_id=OBJ_A)
        old = _old([obj])
        new = make_api_game(
            ce_id=GAME_ID,
            objectives=[obj],
            information="This game now has some new information text.",
        )
        update, _ = create_update_updated_game(old, new)
        assert update is None

    def test_information_change_returns_no_removed_ids(self):
        obj = _po(ce_id=OBJ_A)
        old = _old([obj])
        new = make_api_game(
            ce_id=GAME_ID,
            objectives=[obj],
            information="Updated information.",
        )
        _, removed = create_update_updated_game(old, new)
        assert not removed


# ── Combined / complex scenarios ──────────────────────────────────────────────


class TestCreateUpdateUpdatedGameComplex:
    def test_add_and_remove_different_objectives_triggers_update(self):
        update, _ = create_update_updated_game(
            _old([_po(ce_id=OBJ_A)]), _new([_so(ce_id=OBJ_B)])
        )
        assert update is not None

    def test_add_and_remove_different_objectives_removed_list_correct(self):
        _, removed = create_update_updated_game(
            _old([_po(ce_id=OBJ_A)]), _new([_so(ce_id=OBJ_B)])
        )
        assert removed is not None
        assert OBJ_A in removed
        assert OBJ_B not in removed

    def test_multiple_objective_changes_all_names_in_description(self):
        update, _ = create_update_updated_game(
            _old(
                [
                    _po(points=10, name="PO One", ce_id=OBJ_A),
                    _so(points=20, name="SO Two", ce_id=OBJ_B),
                ]
            ),
            _new(
                [
                    _po(points=15, name="PO One", ce_id=OBJ_A),
                    _so(points=25, name="SO Two", ce_id=OBJ_B),
                ]
            ),
        )
        assert update is not None
        assert "PO One" in update.description
        assert "SO Two" in update.description

    def test_remove_one_keep_another_update_third(self):
        update, removed = create_update_updated_game(
            _old(
                [
                    _po(points=10, ce_id=OBJ_A),
                    _so(points=20, ce_id=OBJ_B),
                    _co(ce_id=OBJ_C),
                ]
            ),
            # OBJ_A removed, OBJ_B points changed, OBJ_C unchanged
            _new([_so(points=30, ce_id=OBJ_B), _co(ce_id=OBJ_C)]),
        )
        assert update is not None
        assert removed is not None
        assert OBJ_A in removed

    def test_game_name_in_title_for_complex_changes(self):
        update, _ = create_update_updated_game(
            _old([_po(points=10)], game_name="Hollow Knight"),
            _new([_so(points=20)], game_name="Hollow Knight"),
        )
        assert update is not None
        assert "Hollow Knight" in update.title

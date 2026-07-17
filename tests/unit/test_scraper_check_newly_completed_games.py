from typing import TYPE_CHECKING

from Classes.CE_Game import CEGame
from Classes.CE_User import MUTELIST_CEIDS
from tests.conftest import make_game, make_objective, make_user
from web_scraper.scraper import check_newly_completed_games

if TYPE_CHECKING:
    from Classes.CE_Objective import CEObjective

MUTED_CE_ID = MUTELIST_CEIDS[0]
GAME_ID = "game-001-0000-0000-000000000000"
GAME_ID_B = "game-002-0000-0000-000000000000"


def _regular_user(display_name: str = "TestUser"):
    return make_user(ce_id="user-001-0000-0000-000000000000", display_name=display_name)


def _muted_user(display_name: str = "MutedUser"):
    return make_user(ce_id=MUTED_CE_ID, display_name=display_name)


def _game(
    po_points: int, so_points: int = 0, ce_id: str = GAME_ID, name: str = "Test Game"
) -> CEGame:
    objectives: list[CEObjective] = []
    if po_points:
        objectives.append(
            make_objective(
                ce_id="po1",
                obj_type="Primary",
                point_value=po_points,
                name="PO",
                game_ce_id=ce_id,
            )
        )
    if so_points:
        objectives.append(
            make_objective(
                ce_id="so1",
                obj_type="Secondary",
                point_value=so_points,
                name="SO",
                game_ce_id=ce_id,
            )
        )
    return make_game(ce_id=ce_id, game_name=name, objectives=objectives)


def _run(
    user,
    completed_old=None,
    completed_new=None,
    overcompleted_old=None,
    overcompleted_new=None,
):
    return check_newly_completed_games(
        completed_old or [],
        completed_new or [],
        user,
        overcompleted_old or [],
        overcompleted_new or [],
    )


# ── completion-only messages ─────────────────────────────────────────────────


class TestCompletionMessage:
    def test_below_tier_minimum_sends_no_message(self):
        # 40 PO points is T3; TIER_MINIMUM is T4.
        game = _game(po_points=40)
        updates = _run(_regular_user(), completed_new=[game])
        assert updates == []

    def test_at_tier_minimum_sends_message(self):
        # 80 PO points is exactly T4.
        game = _game(po_points=80)
        updates = _run(_regular_user(), completed_new=[game])
        assert len(updates) == 1

    def test_already_completed_last_loop_sends_no_message(self):
        game = _game(po_points=80, ce_id=GAME_ID)
        updates = _run(_regular_user(), completed_old=[game], completed_new=[game])
        assert updates == []

    def test_newly_completed_high_tier_sends_message(self):
        game = _game(po_points=200, ce_id=GAME_ID)
        updates = _run(_regular_user(), completed_new=[game])
        assert len(updates) == 1

    def test_message_mentions_user_and_game(self):
        user = _regular_user("Speedster")
        game = _game(po_points=80, name="Celeste")
        updates = _run(user, completed_new=[game])
        assert len(updates) == 1
        assert user.mention in updates[0].text
        assert "Celeste" in updates[0].text

    def test_message_is_not_embed(self):
        game = _game(po_points=80)
        updates = _run(_regular_user(), completed_new=[game])
        assert updates[0].is_embed is False

    def test_regular_user_message_goes_to_userlog(self):
        game = _game(po_points=80)
        updates = _run(_regular_user(), completed_new=[game])
        assert updates[0].location == "userlog"

    def test_muted_user_message_goes_to_privatelog(self):
        game = _game(po_points=80)
        updates = _run(_muted_user(), completed_new=[game])
        assert updates[0].location == "privatelog"

    def test_muted_user_message_has_muted_prefix(self):
        user = _muted_user("SneakyUser")
        game = _game(po_points=80)
        updates = _run(user, completed_new=[game])
        assert "Muted user" in updates[0].text
        assert user.display_name_with_link in updates[0].text

    def test_multiple_newly_completed_games_each_get_a_message(self):
        game_a = _game(po_points=80, ce_id=GAME_ID)
        game_b = _game(po_points=80, ce_id=GAME_ID_B)
        updates = _run(_regular_user(), completed_new=[game_a, game_b])
        assert len(updates) == 2


# ── overcompletion messages — the 6 documented cases ─────────────────────────


class TestOvercompletionDocumentedCases:
    def test_case1_75po_5so_sends_message(self):
        game = _game(po_points=75, so_points=5)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert len(updates) == 1

    def test_case2_150po_10so_sends_no_message(self):
        game = _game(po_points=150, so_points=10)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert updates == []

    def test_case3_150po_80so_sends_message(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert len(updates) == 1

    def test_case4_50po_30so_sends_message(self):
        game = _game(po_points=50, so_points=30)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert len(updates) == 1

    def test_case5_195po_5so_sends_no_message(self):
        game = _game(po_points=195, so_points=5)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert updates == []

    def test_case6_0po_80so_sends_message(self):
        game = _game(po_points=0, so_points=80)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert len(updates) == 1

    def test_low_total_points_below_tier_minimum_sends_no_message(self):
        # 10 PO + 5 SO = 15 total points, well under the T4 (80-point) floor
        # for tier_num_include_so -- skipped before the SO-threshold checks
        # even run.
        game = _game(po_points=10, so_points=5)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert updates == []


class TestOvercompletionMessageDetails:
    def test_already_overcompleted_last_loop_sends_no_message(self):
        game = _game(po_points=150, so_points=80, ce_id=GAME_ID)
        updates = _run(
            _regular_user(), overcompleted_old=[game], overcompleted_new=[game]
        )
        assert updates == []

    def test_message_mentions_overcompleted_wording(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert "over" in updates[0].text.lower()

    def test_message_is_not_embed(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert updates[0].is_embed is False

    def test_muted_user_overcompletion_goes_to_privatelog(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_muted_user(), overcompleted_new=[game])
        assert updates[0].location == "privatelog"

    def test_regular_user_overcompletion_goes_to_userlog(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_regular_user(), overcompleted_new=[game])
        assert updates[0].location == "userlog"


class TestCompletionAndOvercompletionTogether:
    def test_game_newly_completed_and_newly_overcompleted_sends_both_messages(self):
        # A game jumping straight from unstarted to fully overcompleted in one
        # loop should produce both the completion and overcompletion message.
        game = _game(po_points=150, so_points=80, ce_id=GAME_ID)
        updates = _run(_regular_user(), completed_new=[game], overcompleted_new=[game])
        assert len(updates) == 2

    def test_no_games_produces_no_updates(self):
        assert _run(_regular_user()) == []


# ── allowed_mentions gating (ping_user_log) ──────────────────────────────────

# Both the completion loop and the overcompletion loop independently set
# `update.allowed_mentions = user.user_log_pingable_ids` only on the
# non-muted branch; the muted branch never touches it, so a muted user's
# update should always default to the dataclass's empty-list default
# regardless of their ping_user_log preference.


def _pref_user(ping_user_log: bool, discord_id: int = 999):
    return make_user(
        ce_id="user-001-0000-0000-000000000000",
        discord_id=discord_id,
        ping_user_log=ping_user_log,
    )


def _muted_pref_user(ping_user_log: bool):
    return make_user(ce_id=MUTED_CE_ID, ping_user_log=ping_user_log)


class TestAllowedMentionsCompletion:
    def test_pings_when_opted_in(self):
        game = _game(po_points=80)
        updates = _run(_pref_user(True), completed_new=[game])
        assert len(updates) == 1
        assert updates[0].allowed_mentions == [999]

    def test_no_ping_when_opted_out(self):
        game = _game(po_points=80)
        updates = _run(_pref_user(False), completed_new=[game])
        assert len(updates) == 1
        assert updates[0].allowed_mentions == []

    def test_muted_user_never_pings_even_when_opted_in(self):
        game = _game(po_points=80)
        updates = _run(_muted_pref_user(True), completed_new=[game])
        assert len(updates) == 1
        assert updates[0].location == "privatelog"
        assert updates[0].allowed_mentions == []


class TestAllowedMentionsOvercompletion:
    def test_pings_when_opted_in(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_pref_user(True), overcompleted_new=[game])
        assert len(updates) == 1
        assert updates[0].allowed_mentions == [999]

    def test_no_ping_when_opted_out(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_pref_user(False), overcompleted_new=[game])
        assert len(updates) == 1
        assert updates[0].allowed_mentions == []

    def test_muted_user_never_pings_even_when_opted_in(self):
        game = _game(po_points=150, so_points=80)
        updates = _run(_muted_pref_user(True), overcompleted_new=[game])
        assert len(updates) == 1
        assert updates[0].location == "privatelog"
        assert updates[0].allowed_mentions == []

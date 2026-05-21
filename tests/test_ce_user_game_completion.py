import sys
import types
import unittest


def install_dependency_stubs():
    hm = types.ModuleType("Modules.hm")
    hm.PLATFORM_NAMES = str
    hm.CATEGORIES = str
    hm.OBJECTIVE_TYPES = str
    hm.ALL_ROLL_EVENT_NAMES = ()
    sys.modules["Modules.hm"] = hm

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ContentTypeError = type("ContentTypeError", (Exception,), {})
    sys.modules["aiohttp"] = aiohttp

    http_session = types.ModuleType("Modules.http_session")
    sys.modules["Modules.http_session"] = http_session

    cooldown = types.ModuleType("Classes.CE_Cooldown")
    cooldown.CECooldown = type("CECooldown", (), {})
    sys.modules["Classes.CE_Cooldown"] = cooldown

    roll = types.ModuleType("Classes.CE_Roll")
    roll.CERoll = type("CERoll", (), {})
    sys.modules["Classes.CE_Roll"] = roll

    other = types.ModuleType("Classes.OtherClasses")
    other.CRData = type("CRData", (), {})
    other.CECompletion = type("CECompletion", (), {})
    sys.modules["Classes.OtherClasses"] = other


install_dependency_stubs()

import Classes.CE_User as ce_user_module
from Classes.CE_Game import CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective


class CEUserGameCompletionTest(unittest.TestCase):
    def game(self, game_id="game-1", objective_id="objective-1"):
        return CEGame(
            ce_id=game_id,
            game_name="Game",
            platform="steam",
            platform_id="1",
            categories=[],
            objectives=[
                CEObjective(
                    ce_id=objective_id,
                    objective_type="Primary",
                    description="",
                    point_value=10,
                    name="Objective",
                    game_ce_id=game_id,
                )
            ],
            last_updated=0,
        )

    def user_game(self, game_id="game-1", objective_id="objective-1"):
        return CEUserGame(
            ce_id=game_id,
            user_objectives=[
                CEUserObjective(
                    ce_id=objective_id,
                    game_ce_id=game_id,
                    type="Primary",
                    user_points=10,
                )
            ],
            name="Game",
        )

    def user(self, owned_games):
        return CEUser(
            discord_id=1,
            ce_id="user-1",
            owned_games=owned_games,
            rolls=[],
            display_name="User",
            avatar="",
            last_updated=0,
        )

    def test_is_completed_accepts_game_lookup(self):
        game = self.game()

        self.assertTrue(self.user_game().is_completed({"game-1": game}))
        self.assertFalse(self.user_game().is_completed({"other-game": game}))

    def test_get_completed_games_uses_single_lookup_map(self):
        game = self.game()
        user = self.user([self.user_game()])

        ce_user_module.hm.get_item_from_list = self.fail_if_linear_lookup_is_used

        self.assertEqual([game], user.get_completed_games_2([game]))
        self.assertEqual(1, user.completions([game]))

    def fail_if_linear_lookup_is_used(self, *args, **kwargs):
        raise AssertionError("expected CEUser to use a precomputed game lookup")


if __name__ == "__main__":
    unittest.main()

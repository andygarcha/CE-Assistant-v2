# ruff: noqa: E402
import datetime
import importlib.util
import sys
import types


def install_dependency_stubs():
    if importlib.util.find_spec("aiohttp") is None:
        aiohttp = types.ModuleType("aiohttp")
        setattr(aiohttp, "ContentTypeError", type("ContentTypeError", (Exception,), {}))
        setattr(
            aiohttp,
            "ClientConnectionError",
            type("ClientConnectionError", (Exception,), {}),
        )
        setattr(
            aiohttp,
            "ClientTimeout",
            type("ClientTimeout", (), {"__init__": lambda *_, **__: None}),
        )
        setattr(aiohttp, "ClientSession", type("ClientSession", (), {}))
        sys.modules["aiohttp"] = aiohttp

    if importlib.util.find_spec("discord") is None:
        discord = types.ModuleType("discord")
        setattr(discord, "Client", type("Client", (), {}))
        setattr(discord, "Embed", type("Embed", (), {}))
        setattr(discord, "Interaction", type("Interaction", (), {}))
        setattr(discord, "ForumChannel", type("ForumChannel", (), {}))
        setattr(discord, "CategoryChannel", type("CategoryChannel", (), {}))
        setattr(discord, "ConnectionClosed", type("ConnectionClosed", (Exception,), {}))
        setattr(discord, "HTTPException", type("HTTPException", (Exception,), {}))
        setattr(
            discord,
            "AllowedMentions",
            type(
                "AllowedMentions",
                (),
                {
                    "all": staticmethod(lambda: object()),
                    "none": staticmethod(lambda: object()),
                },
            ),
        )
        setattr(
            discord,
            "abc",
            types.SimpleNamespace(
                PrivateChannel=type("PrivateChannel", (), {}),
            ),
        )
        sys.modules["discord"] = discord


install_dependency_stubs()

import Classes.CE_User as ce_user_module
from Classes.CE_Game import CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective


class TestCEUserGameCompletion:
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
            last_updated=None,
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
            last_updated=datetime.datetime.now(),
        )

    def test_is_completed_accepts_game_lookup(self):
        game = self.game()

        assert self.user_game().is_completed({"game-1": game}) is True
        assert self.user_game().is_completed({"other-game": game}) is False

    def test_get_completed_games_uses_single_lookup_map(self, monkeypatch):
        game = self.game()
        user = self.user([self.user_game()])

        monkeypatch.setattr(
            ce_user_module.hm,
            "get_item_from_list",
            self.fail_if_linear_lookup_is_used,
        )

        assert user.get_completed_games_2([game]) == [game]
        assert user.completions([game]) == 1

    def fail_if_linear_lookup_is_used(self, *args, **kwargs):
        raise AssertionError("expected CEUser to use a precomputed game lookup")

import json
import typing
from unittest.mock import patch

from Classes.CE_Game import CEGame
from Modules import hm
from tests.conftest import make_objective
from web_scraper.scraper import generate_database_tier


class _FakeResponse:
    def __init__(self, body):
        self.text = json.dumps(body)


def _steam_game(
    platform_id: str,
    po_points: int = 80,
    ce_id: str | None = None,
    categories: list | None = None,
    platform: str = "steam",
) -> CEGame:
    ce_id = ce_id or f"game-{platform_id}"
    objectives = (
        [
            make_objective(
                ce_id=f"obj-{ce_id}",
                obj_type="Primary",
                point_value=po_points,
                game_ce_id=ce_id,
            )
        ]
        if po_points
        else []
    )
    return CEGame(
        ce_id=ce_id,
        game_name=f"Game {platform_id}",
        platform=platform,  # type: ignore[arg-type]
        platform_id=platform_id,
        categories=categories or ["Action"],  # type: ignore[arg-type]
        objectives=objectives,
        last_updated=None,
    )


def _success_price(appid: str, final: int, discount_percent: int = 0) -> dict:
    return {
        appid: {
            "success": True,
            "data": {
                "price_overview": {"final": final, "discount_percent": discount_percent}
            },
        }
    }


def _empty_price(appid: str) -> dict:
    return {appid: {"success": True, "data": {}}}


def _failed_price(appid: str) -> dict:
    return {appid: {"success": False, "data": {}}}


def _hours_entry(appid: str, minutes: int) -> dict:
    return {"appId": int(appid), "medianCompletionTime": minutes}


def _mock_single_batch(prices_body: dict, hours_body: list):
    """Patches requests.get for exactly one price call + one hours call."""
    return patch(
        "web_scraper.scraper.requests.get",
        side_effect=[_FakeResponse(prices_body), _FakeResponse(hours_body)],
    )


# ── no steam games ────────────────────────────────────────────────────────────


class TestNoSteamGames:
    def test_no_games_makes_no_http_requests(self):
        with patch("web_scraper.scraper.requests.get") as mock_get:
            result = generate_database_tier([])
        mock_get.assert_not_called()
        assert result is not None

    def test_non_steam_games_make_no_http_requests(self):
        game = _steam_game("999", platform="itch")
        with patch("web_scraper.scraper.requests.get") as mock_get:
            result = generate_database_tier([game])
        mock_get.assert_not_called()
        assert result is not None

    def test_returns_dict_shaped_for_every_tier_and_category(self):
        result = generate_database_tier([])
        assert result is not None
        for tier in range(1, 8):
            assert str(tier) in result
            for category in typing.get_args(hm.CATEGORIES):
                assert result[str(tier)][category] == []


# ── malformed API response ────────────────────────────────────────────────────


class TestMalformedPriceResponse:
    def test_list_instead_of_dict_returns_none(self):
        game = _steam_game("220")
        # The Steam price endpoint responding with a list instead of a dict
        # is treated as a hard failure; the hours call is never reached.
        with patch(
            "web_scraper.scraper.requests.get",
            side_effect=[_FakeResponse([1, 2, 3])],
        ):
            result = generate_database_tier([game])
        assert result is None


# ── price extraction branches ─────────────────────────────────────────────────


class TestPriceExtraction:
    def test_successful_price_is_recorded(self):
        game = _steam_game("220", po_points=80)
        prices = _success_price("220", final=999)
        hours = [_hours_entry("220", 600)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert result["4"]["Action"][0]["price"] == 999

    def test_failed_success_flag_excludes_game_from_results(self):
        game = _steam_game("220", po_points=80)
        prices = _failed_price("220")
        hours = [_hours_entry("220", 600)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert result["4"]["Action"] == []

    def test_empty_data_defaults_price_to_zero(self):
        game = _steam_game("220", po_points=80)
        prices = _empty_price("220")
        hours = [_hours_entry("220", 600)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert result["4"]["Action"][0]["price"] == 0

    def test_full_discount_forces_price_to_zero(self):
        game = _steam_game("220", po_points=80)
        prices = _success_price("220", final=1999, discount_percent=100)
        hours = [_hours_entry("220", 600)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert result["4"]["Action"][0]["price"] == 0

    def test_partial_discount_uses_final_price(self):
        game = _steam_game("220", po_points=80)
        prices = _success_price("220", final=1499, discount_percent=25)
        hours = [_hours_entry("220", 600)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert result["4"]["Action"][0]["price"] == 1499


# ── hours extraction branches ─────────────────────────────────────────────────


class TestHoursExtraction:
    def test_successful_hours_is_recorded(self):
        game = _steam_game("220", po_points=80)
        prices = _success_price("220", final=999)
        hours = [_hours_entry("220", 754)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert result["4"]["Action"][0]["sh_hours"] == 754

    def test_missing_median_completion_time_excludes_game(self):
        game = _steam_game("220", po_points=80)
        prices = _success_price("220", final=999)
        hours = [{"appId": 220}]  # no "medianCompletionTime" key
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert result["4"]["Action"] == []


# ── final assembly ─────────────────────────────────────────────────────────────


class TestFinalAssembly:
    def test_t0_game_is_excluded(self):
        game = _steam_game("220", po_points=0)
        prices = _success_price("220", final=0)
        hours = [_hours_entry("220", 0)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        for tier_bucket in result.values():
            for games in tier_bucket.values():
                assert games == []

    def test_multi_category_game_appears_in_every_category_bucket(self):
        game = _steam_game("220", po_points=80, categories=["Action", "Arcade"])
        prices = _success_price("220", final=999)
        hours = [_hours_entry("220", 600)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        assert len(result["4"]["Action"]) == 1
        assert len(result["4"]["Arcade"]) == 1
        assert result["4"]["Action"][0]["ce_id"] == game.ce_id
        assert result["4"]["Arcade"][0]["ce_id"] == game.ce_id

    def test_entry_contains_ce_id_price_and_hours(self):
        game = _steam_game("220", po_points=80, ce_id="my-game-id")
        prices = _success_price("220", final=1234)
        hours = [_hours_entry("220", 42)]
        with _mock_single_batch(prices, hours):
            result = generate_database_tier([game])
        assert result is not None
        entry = result["4"]["Action"][0]
        assert entry == {"ce_id": "my-game-id", "price": 1234, "sh_hours": 42}


# ── batching ─────────────────────────────────────────────────────────────────


class TestBatching:
    def test_over_100_steam_games_issues_two_batches_of_requests(self):
        games = [_steam_game(str(i), po_points=80) for i in range(1, 102)]

        prices_batch_1 = {}
        hours_batch_1 = []
        for i in range(1, 101):
            prices_batch_1.update(_success_price(str(i), final=100))
            hours_batch_1.append(_hours_entry(str(i), 60))

        prices_batch_2 = _success_price("101", final=200)
        hours_batch_2 = [_hours_entry("101", 120)]

        with patch(
            "web_scraper.scraper.requests.get",
            side_effect=[
                _FakeResponse(prices_batch_1),
                _FakeResponse(hours_batch_1),
                _FakeResponse(prices_batch_2),
                _FakeResponse(hours_batch_2),
            ],
        ) as mock_get:
            result = generate_database_tier(games)

        assert mock_get.call_count == 4
        assert result is not None
        assert len(result["4"]["Action"]) == 101

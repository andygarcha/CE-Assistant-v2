from unittest.mock import patch
from web_scraper.scraper import flush_updates, UpdateMessageForScraperProcess


def _make_update(**kwargs) -> UpdateMessageForScraperProcess:
    return UpdateMessageForScraperProcess(**kwargs)


class TestFlushUpdatesRouting:
    def test_non_game_update_goes_to_stable(self):
        update = _make_update(
            is_embed=False, location="casino", text="You won!", game_ce_id=None
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([update])

        mock_upsert.assert_not_called()
        mock_bulk.assert_called_once()
        rows = mock_bulk.call_args[0][0]
        assert len(rows) == 1
        assert rows[0]["status"] == "stable"
        assert rows[0]["channel"] == "casino"
        assert rows[0]["text"] == "You won!"

    def test_game_update_goes_to_pending(self):
        update = _make_update(
            is_embed=True,
            location="gameadditions",
            title="New Game!",
            game_ce_id="game-001",
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([update])

        mock_bulk.assert_not_called()
        mock_upsert.assert_called_once()
        row = mock_upsert.call_args[0][0]
        assert row["status"] == "pending"
        assert row["game_ce_id"] == "game-001"
        assert row["channel"] == "gameadditions"

    def test_mixed_updates_routed_correctly(self):
        game_update = _make_update(
            is_embed=True,
            location="gameadditions",
            title="Updated!",
            game_ce_id="game-002",
        )
        roll_update = _make_update(
            is_embed=False, location="casino", text="Roll won!", game_ce_id=None
        )
        user_update = _make_update(
            is_embed=False, location="userlog", text="Rank up!", game_ce_id=None
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([game_update, roll_update, user_update])

        mock_upsert.assert_called_once()
        assert mock_upsert.call_args[0][0]["game_ce_id"] == "game-002"

        mock_bulk.assert_called_once()
        rows = mock_bulk.call_args[0][0]
        assert len(rows) == 2
        assert all(r["status"] == "stable" for r in rows)
        assert {r["channel"] for r in rows} == {"casino", "userlog"}

    def test_null_location_skipped(self):
        update = _make_update(location=None, text="orphan message")

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([update])

        mock_bulk.assert_not_called()
        mock_upsert.assert_not_called()

    def test_empty_list_is_noop(self):
        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([])

        mock_bulk.assert_not_called()
        mock_upsert.assert_not_called()

    def test_row_fields_match_dataclass(self):
        update = _make_update(
            is_embed=True,
            location="gameadditions",
            text="",
            title="Celeste updated",
            description="Points changed",
            image="https://example.com/img.png",
            url="https://cedb.me/game/abc",
            color=0xEFD839,
            game_ce_id="abc",
        )

        with (
            patch("web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"),
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([update])

        row = mock_upsert.call_args[0][0]
        assert row["is_embed"] is True
        assert row["channel"] == "gameadditions"
        assert row["text"] == ""
        assert row["title"] == "Celeste updated"
        assert row["description"] == "Points changed"
        assert row["image"] == "https://example.com/img.png"
        assert row["url"] == "https://cedb.me/game/abc"
        assert row["color"] == 0xEFD839
        assert row["game_ce_id"] == "abc"
        assert row["status"] == "pending"


class TestFlushUpdatesMultipleGameUpdates:
    def test_each_game_update_upserted_individually(self):
        updates = [
            _make_update(location="gameadditions", title="Game A", game_ce_id="game-a"),
            _make_update(location="gameadditions", title="Game B", game_ce_id="game-b"),
            _make_update(location="gameadditions", title="Game C", game_ce_id="game-c"),
        ]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates(updates)

        assert mock_upsert.call_count == 3
        upserted_ids = [c[0][0]["game_ce_id"] for c in mock_upsert.call_args_list]
        assert upserted_ids == ["game-a", "game-b", "game-c"]
        mock_bulk.assert_not_called()

    def test_duplicate_game_ids_each_upserted(self):
        updates = [
            _make_update(
                location="gameadditions", title="First change", game_ce_id="game-x"
            ),
            _make_update(
                location="gameadditions", title="Second change", game_ce_id="game-x"
            ),
        ]

        with (
            patch("web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"),
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates(updates)

        assert mock_upsert.call_count == 2
        assert mock_upsert.call_args_list[0][0][0]["title"] == "First change"
        assert mock_upsert.call_args_list[1][0][0]["title"] == "Second change"


class TestFlushUpdatesNullLocationMixed:
    def test_null_location_among_valid_updates(self):
        updates = [
            _make_update(location="casino", text="valid", game_ce_id=None),
            _make_update(location=None, text="orphan"),
            _make_update(location="gameadditions", title="game", game_ce_id="g1"),
        ]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates(updates)

        mock_bulk.assert_called_once()
        assert len(mock_bulk.call_args[0][0]) == 1
        assert mock_bulk.call_args[0][0][0]["channel"] == "casino"

        mock_upsert.assert_called_once()
        assert mock_upsert.call_args[0][0]["game_ce_id"] == "g1"

    def test_all_null_locations_is_noop(self):
        updates = [
            _make_update(location=None, text="a"),
            _make_update(location=None, text="b"),
        ]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates(updates)

        mock_bulk.assert_not_called()
        mock_upsert.assert_not_called()


class TestFlushUpdatesDefaults:
    def test_default_dataclass_values_serialized(self):
        update = _make_update(location="userlog")

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch("web_scraper.scraper.SupabaseReader.upsert_pending_update"),
        ):
            flush_updates([update])

        row = mock_bulk.call_args[0][0][0]
        assert row["is_embed"] is False
        assert row["text"] == ""
        assert row["title"] == ""
        assert row["description"] == ""
        assert row["image"] == ""
        assert row["url"] == ""
        assert row["color"] == 0
        assert row["game_ce_id"] is None
        assert row["status"] == "stable"

    def test_embed_fields_preserved_for_non_game_embed(self):
        update = _make_update(
            is_embed=True,
            location="casinolog",
            title="Roll Complete",
            description="You completed your roll!",
            image="https://example.com/trophy.png",
            url="https://cedb.me/user/123",
            color=0x00FF00,
            game_ce_id=None,
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch("web_scraper.scraper.SupabaseReader.upsert_pending_update"),
        ):
            flush_updates([update])

        row = mock_bulk.call_args[0][0][0]
        assert row["is_embed"] is True
        assert row["title"] == "Roll Complete"
        assert row["description"] == "You completed your roll!"
        assert row["image"] == "https://example.com/trophy.png"
        assert row["url"] == "https://cedb.me/user/123"
        assert row["color"] == 0x00FF00
        assert row["status"] == "stable"


class TestFlushUpdatesChannelVariety:
    def test_all_channel_types_routed_as_stable(self):
        channels = ["casino", "casinolog", "userlog", "privatelog"]
        updates = [_make_update(location=ch, text=f"msg to {ch}") for ch in channels]

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates(updates)

        mock_upsert.assert_not_called()
        rows = mock_bulk.call_args[0][0]
        assert len(rows) == 4
        assert all(r["status"] == "stable" for r in rows)
        assert [r["channel"] for r in rows] == channels

    def test_gameadditions_without_game_ce_id_goes_stable(self):
        update = _make_update(
            location="gameadditions", text="some non-game message", game_ce_id=None
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([update])

        mock_upsert.assert_not_called()
        mock_bulk.assert_called_once()
        assert mock_bulk.call_args[0][0][0]["status"] == "stable"

    def test_non_gameadditions_channel_with_game_ce_id_goes_pending(self):
        update = _make_update(
            location="casino", text="roll for game", game_ce_id="game-123"
        )

        with (
            patch(
                "web_scraper.scraper.SupabaseReader.write_scraper_updates_bulk"
            ) as mock_bulk,
            patch(
                "web_scraper.scraper.SupabaseReader.upsert_pending_update"
            ) as mock_upsert,
        ):
            flush_updates([update])

        mock_upsert.assert_called_once()
        assert mock_upsert.call_args[0][0]["status"] == "pending"
        mock_bulk.assert_not_called()

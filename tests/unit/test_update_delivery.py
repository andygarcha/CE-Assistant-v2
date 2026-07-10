import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from update_delivery import deliver_updates


@pytest.fixture(autouse=True)
def _mock_delivery_deps():
    recent = datetime.datetime.now(datetime.UTC)
    with (
        patch(
            "update_delivery.SupabaseReader.get_pending_game_updates",
            return_value=[],
        ),
        patch(
            "update_delivery.SupabaseReader.get_last_loop",
            return_value=recent,
        ),
        patch(
            "update_delivery.hm.send_message",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        yield


def _find_call(mock_send: AsyncMock, channel: str):
    for call in mock_send.call_args_list:
        if call.args[1] == channel:
            return call
    raise AssertionError(f"no send_message call found for channel {channel!r}")


def _find_privatelog_call(mock_send: AsyncMock, substring: str):
    for call in mock_send.call_args_list:
        if call.args[1] == "privatelog" and substring in call.args[2]:
            return call
    raise AssertionError(f"no privatelog call found containing {substring!r}")


class TestDeliverUpdates:
    def test_sends_text_update(self):
        mock_client = MagicMock()
        updates = [
            {
                "id": "u1",
                "is_embed": False,
                "channel": "casino",
                "text": "You won!",
                "title": "",
                "description": "",
                "image": "",
                "url": "",
                "color": 0,
            }
        ]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            count = asyncio.run(deliver_updates(mock_client))

        assert mock_send.await_count == 2
        call_args = _find_call(mock_send, "casino")
        assert call_args.args[0] is mock_client
        assert call_args.args[1] == "casino"
        assert call_args.args[2] == "You won!"
        mock_mark.assert_called_once_with(["u1"])
        assert count == 1

    def test_sends_embed_update(self):
        mock_client = MagicMock()
        updates = [
            {
                "id": "u2",
                "is_embed": True,
                "channel": "gameadditions",
                "text": "",
                "title": "New Game!",
                "description": "A cool game",
                "image": "https://example.com/img.png",
                "url": "https://cedb.me/game/123",
                "color": 0x48B474,
            }
        ]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            count = asyncio.run(deliver_updates(mock_client))

        assert mock_send.await_count == 2
        call_kwargs = _find_call(mock_send, "gameadditions")
        embed = call_kwargs.kwargs["embed"]
        assert embed.title == "New Game!"
        assert embed.description == "A cool game"
        mock_mark.assert_called_once_with(["u2"])
        assert count == 1

    def test_no_updates_is_noop(self):
        mock_client = MagicMock()

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=[]),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            count = asyncio.run(deliver_updates(mock_client))

        # no updates and a recent (non-stale) loop: nothing gets sent at all
        mock_send.assert_not_awaited()
        mock_mark.assert_not_called()
        assert count == 0

    def test_no_checking_message_when_recent(self):
        mock_client = MagicMock()
        recent = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)

        with (
            patch("update_delivery.SupabaseReader.get_last_loop", return_value=recent),
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=[]),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            asyncio.run(deliver_updates(mock_client))

        mock_send.assert_not_awaited()

    def test_checking_message_warns_when_scraper_stale(self):
        mock_client = MagicMock()
        stale = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)

        with (
            patch("update_delivery.SupabaseReader.get_last_loop", return_value=stale),
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=[]),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            asyncio.run(deliver_updates(mock_client))

        check_call = _find_privatelog_call(mock_send, ":mag:")
        assert ":warning:" in check_call.args[2]
        assert "more than an hour ago" in check_call.args[2]

    def test_logs_and_announces_when_sending(self, caplog):
        mock_client = MagicMock()
        updates = [
            {
                "id": "u1",
                "is_embed": False,
                "channel": "casino",
                "text": "You won!",
                "title": "",
                "description": "",
                "image": "",
                "url": "",
                "color": 0,
            }
        ]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch(
                "update_delivery.SupabaseReader.get_pending_game_updates",
                return_value=[{"id": "p1"}, {"id": "p2"}],
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered"),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
            caplog.at_level("INFO", logger="update_delivery"),
        ):
            asyncio.run(deliver_updates(mock_client))

        expected = ":information_source: Sending 1 message (2 not ready yet)."
        assert expected in caplog.text
        privatelog_call = _find_privatelog_call(mock_send, "Sending 1 message")
        assert privatelog_call.args[2] == expected
        assert privatelog_call.args[3] is False

    def test_logs_and_announces_when_nothing_stable_but_some_pending(self, caplog):
        mock_client = MagicMock()

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=[]),
            patch(
                "update_delivery.SupabaseReader.get_pending_game_updates",
                return_value=[{"id": "p1"}],
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered"),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
            caplog.at_level("INFO", logger="update_delivery"),
        ):
            count = asyncio.run(deliver_updates(mock_client))

        assert count == 0
        expected = ":information_source: Nothing stable to send yet (1 not ready yet)."
        assert expected in caplog.text
        nothing_stable_call = _find_privatelog_call(mock_send, "Nothing stable")
        assert nothing_stable_call.args[2] == expected

    def test_multiple_updates_marks_per_row(self):
        mock_client = MagicMock()
        updates = [
            {
                "id": "u1",
                "is_embed": False,
                "channel": "casino",
                "text": "msg1",
                "title": "",
                "description": "",
                "image": "",
                "url": "",
                "color": 0,
            },
            {
                "id": "u2",
                "is_embed": False,
                "channel": "userlog",
                "text": "msg2",
                "title": "",
                "description": "",
                "image": "",
                "url": "",
                "color": 0,
            },
        ]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            count = asyncio.run(deliver_updates(mock_client))

        assert mock_send.await_count == 3
        assert mock_mark.call_count == 2
        mock_mark.assert_any_call(["u1"])
        mock_mark.assert_any_call(["u2"])
        assert count == 2

    def test_failed_send_not_marked_delivered(self):
        mock_client = MagicMock()
        updates = [
            {
                "id": "u1",
                "is_embed": False,
                "channel": "casino",
                "text": "You won!",
                "title": "",
                "description": "",
                "image": "",
                "url": "",
                "color": 0,
            }
        ]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            count = asyncio.run(deliver_updates(mock_client))

        mock_mark.assert_not_called()
        assert count == 0

    def test_partial_failure_only_marks_successful(self):
        mock_client = MagicMock()
        updates = [
            {
                "id": "u1",
                "is_embed": False,
                "channel": "casino",
                "text": "msg1",
                "title": "",
                "description": "",
                "image": "",
                "url": "",
                "color": 0,
            },
            {
                "id": "u2",
                "is_embed": False,
                "channel": "badchannel",
                "text": "msg2",
                "title": "",
                "description": "",
                "image": "",
                "url": "",
                "color": 0,
            },
        ]

        def _side_effect(
            client, channel, message="", allowed_mentions=True, embed=None
        ):
            return channel != "badchannel"

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                side_effect=_side_effect,
            ),
        ):
            count = asyncio.run(deliver_updates(mock_client))

        mock_mark.assert_called_once_with(["u1"])
        assert count == 1


class TestDeliverUpdatesExceptionRecovery:
    """An exception from send_message (not just False return) propagates to
    the caller. The caller (delivery_loop in main.py) catches it so the
    bot doesn't crash."""

    def _make_update(self, id: str, text: str = "msg") -> dict:
        return {
            "id": id,
            "is_embed": False,
            "channel": "casino",
            "text": text,
            "title": "",
            "description": "",
            "image": "",
            "url": "",
            "color": 0,
        }

    def test_exception_on_send_propagates(self):
        mock_client = MagicMock()
        updates = [self._make_update("u1")]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered"),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                side_effect=discord.HTTPException(MagicMock(), "server error"),
            ),
            pytest.raises(discord.HTTPException),
        ):
            asyncio.run(deliver_updates(mock_client))

    def test_get_stable_updates_exception_propagates(self):
        mock_client = MagicMock()

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                side_effect=Exception("supabase down"),
            ),
            pytest.raises(Exception, match="supabase down"),
        ):
            asyncio.run(deliver_updates(mock_client))

    def test_get_last_loop_exception_propagates(self):
        mock_client = MagicMock()

        with (
            patch(
                "update_delivery.SupabaseReader.get_last_loop",
                side_effect=Exception("supabase down"),
            ),
            pytest.raises(Exception, match="supabase down"),
        ):
            asyncio.run(deliver_updates(mock_client))


class TestDeliverUpdatesEmbedConstruction:
    """Verify embed details beyond just title/description."""

    def _make_embed_update(self, **overrides) -> dict:
        defaults = {
            "id": "u1",
            "is_embed": True,
            "channel": "gameadditions",
            "text": "",
            "title": "Game Title",
            "description": "Description",
            "image": "https://example.com/img.png",
            "url": "https://cedb.me/game/123",
            "color": 0x48B474,
        }
        defaults.update(overrides)
        return defaults

    def test_embed_uses_fallback_image_when_empty(self):
        mock_client = MagicMock()
        updates = [self._make_embed_update(image="")]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered"),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            asyncio.run(deliver_updates(mock_client))

        embed = _find_call(mock_send, "gameadditions").kwargs["embed"]
        assert embed.image.url is not None
        assert embed.image.url != ""

    def test_embed_has_author_and_footer(self):
        mock_client = MagicMock()
        updates = [self._make_embed_update()]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered"),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            asyncio.run(deliver_updates(mock_client))

        embed = _find_call(mock_send, "gameadditions").kwargs["embed"]
        assert embed.author.name == "Challenge Enthusiasts"
        assert embed.footer.text == "CE Assistant"
        assert embed.timestamp is not None

    def test_embed_color_and_url_set(self):
        mock_client = MagicMock()
        updates = [
            self._make_embed_update(color=0xFF0000, url="https://cedb.me/game/abc")
        ]

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered"),
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_send,
        ):
            asyncio.run(deliver_updates(mock_client))

        embed = _find_call(mock_send, "gameadditions").kwargs["embed"]
        assert embed.color.value == 0xFF0000
        assert embed.url == "https://cedb.me/game/abc"

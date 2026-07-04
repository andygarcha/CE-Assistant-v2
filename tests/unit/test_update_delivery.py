import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from update_delivery import deliver_updates


@pytest.fixture(autouse=True)
def _mock_pending_updates():
    with patch(
        "update_delivery.SupabaseReader.get_pending_game_updates", return_value=[]
    ):
        yield


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

        mock_send.assert_awaited_once()
        call_args = mock_send.call_args
        assert call_args[0][0] is mock_client
        assert call_args[0][1] == "casino"
        assert call_args[0][2] == "You won!"
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

        mock_send.assert_awaited_once()
        call_kwargs = mock_send.call_args
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
                "update_delivery.hm.send_message", new_callable=AsyncMock
            ) as mock_send,
        ):
            count = asyncio.run(deliver_updates(mock_client))

        mock_send.assert_not_awaited()
        mock_mark.assert_not_called()
        assert count == 0

    def test_logs_pending_count_when_sending(self, caplog):
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
            ),
            caplog.at_level("INFO", logger="update_delivery"),
        ):
            asyncio.run(deliver_updates(mock_client))

        assert "Sending 1 message (2 not ready yet)" in caplog.text

    def test_logs_when_nothing_stable_but_some_pending(self, caplog):
        mock_client = MagicMock()

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=[]),
            patch(
                "update_delivery.SupabaseReader.get_pending_game_updates",
                return_value=[{"id": "p1"}],
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered"),
            patch("update_delivery.hm.send_message", new_callable=AsyncMock),
            caplog.at_level("INFO", logger="update_delivery"),
        ):
            count = asyncio.run(deliver_updates(mock_client))

        assert count == 0
        assert "Nothing stable to send yet (1 not ready yet)" in caplog.text

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

        assert mock_send.await_count == 2
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

        with (
            patch(
                "update_delivery.SupabaseReader.get_stable_updates",
                return_value=updates,
            ),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch(
                "update_delivery.hm.send_message",
                new_callable=AsyncMock,
                side_effect=[True, False],
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
        ):
            with __import__("pytest").raises(discord.HTTPException):
                asyncio.run(deliver_updates(mock_client))

    def test_get_stable_updates_exception_propagates(self):
        mock_client = MagicMock()

        with patch(
            "update_delivery.SupabaseReader.get_stable_updates",
            side_effect=Exception("supabase down"),
        ):
            with __import__("pytest").raises(Exception, match="supabase down"):
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

        embed = mock_send.call_args.kwargs["embed"]
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

        embed = mock_send.call_args.kwargs["embed"]
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

        embed = mock_send.call_args.kwargs["embed"]
        assert embed.color.value == 0xFF0000
        assert embed.url == "https://cedb.me/game/abc"

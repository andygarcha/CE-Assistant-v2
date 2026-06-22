import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from update_delivery import deliver_updates


class TestDeliverUpdates:
    def test_sends_text_update(self):
        mock_client = MagicMock()
        updates = [{
            "id": "u1",
            "is_embed": False,
            "channel": "casino",
            "text": "You won!",
            "title": "",
            "description": "",
            "image": "",
            "url": "",
            "color": 0,
        }]

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=updates),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch("update_delivery.hm.send_message", new_callable=AsyncMock, return_value=True) as mock_send,
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
        updates = [{
            "id": "u2",
            "is_embed": True,
            "channel": "gameadditions",
            "text": "",
            "title": "New Game!",
            "description": "A cool game",
            "image": "https://example.com/img.png",
            "url": "https://cedb.me/game/123",
            "color": 0x48B474,
        }]

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=updates),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch("update_delivery.hm.send_message", new_callable=AsyncMock, return_value=True) as mock_send,
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
            patch("update_delivery.hm.send_message", new_callable=AsyncMock) as mock_send,
        ):
            count = asyncio.run(deliver_updates(mock_client))

        mock_send.assert_not_awaited()
        mock_mark.assert_not_called()
        assert count == 0

    def test_multiple_updates_marks_per_row(self):
        mock_client = MagicMock()
        updates = [
            {"id": "u1", "is_embed": False, "channel": "casino", "text": "msg1",
             "title": "", "description": "", "image": "", "url": "", "color": 0},
            {"id": "u2", "is_embed": False, "channel": "userlog", "text": "msg2",
             "title": "", "description": "", "image": "", "url": "", "color": 0},
        ]

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=updates),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch("update_delivery.hm.send_message", new_callable=AsyncMock, return_value=True) as mock_send,
        ):
            count = asyncio.run(deliver_updates(mock_client))

        assert mock_send.await_count == 2
        assert mock_mark.call_count == 2
        mock_mark.assert_any_call(["u1"])
        mock_mark.assert_any_call(["u2"])
        assert count == 2

    def test_failed_send_not_marked_delivered(self):
        mock_client = MagicMock()
        updates = [{
            "id": "u1",
            "is_embed": False,
            "channel": "casino",
            "text": "You won!",
            "title": "",
            "description": "",
            "image": "",
            "url": "",
            "color": 0,
        }]

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=updates),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch("update_delivery.hm.send_message", new_callable=AsyncMock, return_value=False),
        ):
            count = asyncio.run(deliver_updates(mock_client))

        mock_mark.assert_not_called()
        assert count == 0

    def test_partial_failure_only_marks_successful(self):
        mock_client = MagicMock()
        updates = [
            {"id": "u1", "is_embed": False, "channel": "casino", "text": "msg1",
             "title": "", "description": "", "image": "", "url": "", "color": 0},
            {"id": "u2", "is_embed": False, "channel": "badchannel", "text": "msg2",
             "title": "", "description": "", "image": "", "url": "", "color": 0},
        ]

        with (
            patch("update_delivery.SupabaseReader.get_stable_updates", return_value=updates),
            patch("update_delivery.SupabaseReader.mark_updates_delivered") as mock_mark,
            patch("update_delivery.hm.send_message", new_callable=AsyncMock, side_effect=[True, False]),
        ):
            count = asyncio.run(deliver_updates(mock_client))

        mock_mark.assert_called_once_with(["u1"])
        assert count == 1

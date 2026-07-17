import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import discord

from utils.channels import send_message


def _channel() -> MagicMock:
    channel = MagicMock()
    channel.send = AsyncMock()
    return channel


def _client(channel: MagicMock) -> MagicMock:
    client = MagicMock()
    client.get_channel.return_value = channel
    return client


def _sent_mentions(channel: MagicMock) -> discord.AllowedMentions:
    "Pulls the `allowed_mentions` kwarg passed to `channel.send` out of the mock."
    return channel.send.await_args.kwargs["allowed_mentions"]


# ── bool branch (legacy all-or-nothing) ──────────────────────────────────────


class TestAllowedMentionsBoolBranch:
    def test_true_pings_everyone(self):
        channel = _channel()
        asyncio.run(send_message(_client(channel), "casino", "hi", True))
        assert (
            _sent_mentions(channel).to_dict() == discord.AllowedMentions.all().to_dict()
        )

    def test_false_pings_no_one(self):
        channel = _channel()
        asyncio.run(send_message(_client(channel), "casino", "hi", False))
        assert (
            _sent_mentions(channel).to_dict()
            == discord.AllowedMentions.none().to_dict()
        )

    def test_default_param_pings_everyone(self):
        channel = _channel()
        asyncio.run(send_message(_client(channel), "casino", "hi"))
        assert (
            _sent_mentions(channel).to_dict() == discord.AllowedMentions.all().to_dict()
        )


# ── list branch (targeted opt-in pings) ──────────────────────────────────────


class TestAllowedMentionsListBranch:
    def test_list_of_ids_only_pings_those_users(self):
        channel = _channel()
        asyncio.run(send_message(_client(channel), "casino", "hi", [111, 222]))
        assert _sent_mentions(channel).to_dict() == {
            "parse": [],
            "users": [111, 222],
            "replied_user": True,
        }

    def test_single_id_list(self):
        channel = _channel()
        asyncio.run(send_message(_client(channel), "casino", "hi", [555]))
        assert _sent_mentions(channel).to_dict() == {
            "parse": [],
            "users": [555],
            "replied_user": True,
        }

    def test_empty_list_pings_no_one(self):
        # Distinct from allowed_mentions=False: to_dict() still declares an
        # (empty) `users` allowlist rather than omitting the key entirely, so
        # a future refactor can't accidentally collapse `[]` into the bool
        # branch's `AllowedMentions.none()` shape without a test noticing.
        channel = _channel()
        asyncio.run(send_message(_client(channel), "casino", "hi", []))
        mentions = _sent_mentions(channel)
        assert mentions.to_dict() == {"parse": [], "users": [], "replied_user": True}
        assert mentions.to_dict() != discord.AllowedMentions.none().to_dict()

    def test_duplicate_ids_are_preserved(self):
        # Documents current behavior: send_message doesn't dedupe, so a
        # caller that accidentally lists the same user twice (e.g. co-op
        # rolls with two accounts controlled by one person) just sends a
        # list with a duplicate; Discord's API tolerates this.
        channel = _channel()
        asyncio.run(send_message(_client(channel), "casino", "hi", [111, 111]))
        assert _sent_mentions(channel).to_dict()["users"] == [111, 111]

    def test_list_never_allows_everyone_or_role_pings(self):
        # Even if the message text contains @everyone or a role mention, the
        # list branch must keep those locked down -- only the specific user
        # IDs given should be pingable.
        channel = _channel()
        asyncio.run(
            send_message(_client(channel), "casino", "@everyone @here <@&12345>", [111])
        )
        mentions = _sent_mentions(channel)
        assert mentions.everyone is False
        assert mentions.roles is False


# ── channel resolution failures ──────────────────────────────────────────────


class TestChannelNotFound:
    def test_returns_false_and_never_sends_when_channel_missing(self):
        channel = _channel()
        client = _client(channel)
        client.get_channel.return_value = None
        result = asyncio.run(send_message(client, "casino", "hi", [111]))
        assert result is False
        channel.send.assert_not_awaited()

    def test_returns_false_when_client_is_none(self):
        result = asyncio.run(send_message(None, "casino", "hi", [111]))
        assert result is False


# ── send failures are swallowed into a bool ──────────────────────────────────


class TestSendFailureHandling:
    def test_returns_false_on_http_exception_with_list_mentions(self):
        channel = _channel()
        channel.send.side_effect = discord.HTTPException(MagicMock(), "server error")
        result = asyncio.run(send_message(_client(channel), "casino", "hi", [111]))
        assert result is False

    def test_returns_false_on_connection_error_with_list_mentions(self):
        channel = _channel()
        channel.send.side_effect = aiohttp.ClientConnectionError()
        result = asyncio.run(send_message(_client(channel), "casino", "hi", [111]))
        assert result is False

    def test_returns_true_on_success_with_list_mentions(self):
        channel = _channel()
        result = asyncio.run(send_message(_client(channel), "casino", "hi", [111]))
        assert result is True


# ── embed path also respects allowed_mentions ────────────────────────────────


class TestEmbedPathMentions:
    def test_embed_send_receives_list_mentions(self):
        channel = _channel()
        embed = discord.Embed(title="t")
        asyncio.run(
            send_message(_client(channel), "casino", "hi", [111, 222], embed=embed)
        )
        _, kwargs = channel.send.await_args
        assert kwargs["allowed_mentions"].to_dict() == {
            "parse": [],
            "users": [111, 222],
            "replied_user": True,
        }
        assert kwargs["embed"] is embed

    def test_embed_send_receives_bool_mentions(self):
        channel = _channel()
        embed = discord.Embed(title="t")
        asyncio.run(send_message(_client(channel), "casino", "hi", False, embed=embed))
        _, kwargs = channel.send.await_args
        assert (
            kwargs["allowed_mentions"].to_dict()
            == discord.AllowedMentions.none().to_dict()
        )

    def test_embed_returns_false_on_http_exception(self):
        channel = _channel()
        channel.send.side_effect = discord.HTTPException(MagicMock(), "server error")
        embed = discord.Embed(title="t")
        result = asyncio.run(
            send_message(_client(channel), "casino", "hi", [111], embed=embed)
        )
        assert result is False

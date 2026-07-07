import asyncio
from unittest.mock import AsyncMock, patch

from utils.emoji_cache import parse_emoji_id, get_cached_emoji_path


class TestParseEmojiId:
    def test_parses_standard_emoji(self):
        assert parse_emoji_id("<:tier1:1126268393725644810>") == "1126268393725644810"

    def test_parses_animated_emoji(self):
        assert parse_emoji_id("<a:wiggle:123456789012345678>") == "123456789012345678"

    def test_returns_none_for_non_emoji_string(self):
        assert parse_emoji_id("not an emoji") is None
        assert parse_emoji_id("bad-input") is None


class _FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    async def read(self) -> bytes:
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.get_calls: list[str] = []

    def get(self, url: str):
        self.get_calls.append(url)
        return self._response


class TestGetCachedEmojiPath:
    def test_returns_none_for_unparseable_markup(self, tmp_path):
        result = asyncio.run(
            get_cached_emoji_path("bad-input", cache_dir=tmp_path)
        )
        assert result is None

    def test_returns_cached_path_without_network_call(self, tmp_path):
        emoji_id = "1126268393725644810"
        cached_file = tmp_path / f"{emoji_id}.png"
        cached_file.write_bytes(b"fake-png-bytes")

        with patch(
            "utils.emoji_cache.http_session.get_session", new_callable=AsyncMock
        ) as mock_get_session:
            result = asyncio.run(
                get_cached_emoji_path(f"<:tier1:{emoji_id}>", cache_dir=tmp_path)
            )

        assert result == cached_file
        mock_get_session.assert_not_called()

    def test_downloads_and_caches_on_miss(self, tmp_path):
        emoji_id = "1126268393725644810"
        fake_session = _FakeSession(_FakeResponse(200, b"downloaded-bytes"))

        with patch(
            "utils.emoji_cache.http_session.get_session",
            new_callable=AsyncMock,
            return_value=fake_session,
        ):
            result = asyncio.run(
                get_cached_emoji_path(f"<:tier1:{emoji_id}>", cache_dir=tmp_path)
            )

        assert result == tmp_path / f"{emoji_id}.png"
        assert result.read_bytes() == b"downloaded-bytes"
        assert fake_session.get_calls == [
            f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
        ]

    def test_returns_none_on_http_error(self, tmp_path):
        emoji_id = "1126268393725644810"
        fake_session = _FakeSession(_FakeResponse(404, b""))

        with patch(
            "utils.emoji_cache.http_session.get_session",
            new_callable=AsyncMock,
            return_value=fake_session,
        ):
            result = asyncio.run(
                get_cached_emoji_path(f"<:tier1:{emoji_id}>", cache_dir=tmp_path)
            )

        assert result is None
        assert not (tmp_path / f"{emoji_id}.png").exists()

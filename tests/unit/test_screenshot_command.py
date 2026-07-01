import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from commands.screenshot import get_screenshot


def _make_interaction() -> SimpleNamespace:
    return SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        user=SimpleNamespace(id=1, name="tester"),
    )


def _run(interaction, game="abc-123"):
    import commands.screenshot as screenshot_mod

    with (
        patch.object(screenshot_mod, "client", create=True, new=MagicMock()),
        patch("commands.screenshot.hm.log_command", new_callable=AsyncMock),
    ):
        asyncio.run(get_screenshot(interaction, game))


def test_sends_file_on_success():
    interaction = _make_interaction()

    with (
        patch(
            "commands.screenshot.http_session.get_session",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "commands.screenshot.PiScreenshot.fetch_screenshot",
            new_callable=AsyncMock,
            return_value=b"\x89PNG...",
        ),
    ):
        _run(interaction)

    interaction.followup.send.assert_called_once()
    _, kwargs = interaction.followup.send.call_args
    assert "file" in kwargs
    assert kwargs["file"].filename == "abc-123.png"


def test_sends_error_message_on_screenshot_failure():
    from Modules.PiScreenshot import ScreenshotError

    interaction = _make_interaction()

    with (
        patch(
            "commands.screenshot.http_session.get_session",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "commands.screenshot.PiScreenshot.fetch_screenshot",
            new_callable=AsyncMock,
            side_effect=ScreenshotError("504: timed out"),
        ),
    ):
        _run(interaction)

    msg = interaction.followup.send.call_args[0][0]
    assert "504: timed out" in msg


def test_defers_response():
    interaction = _make_interaction()

    with (
        patch(
            "commands.screenshot.http_session.get_session",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "commands.screenshot.PiScreenshot.fetch_screenshot",
            new_callable=AsyncMock,
            return_value=b"\x89PNG...",
        ),
    ):
        _run(interaction)

    interaction.response.defer.assert_called_once()

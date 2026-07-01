import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from commands.screenshot import _format_timings, get_diff_screenshot, get_screenshot


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


_DEFAULT_TIMINGS = {
    "X-Timing-Warmup": "2.00",
    "X-Timing-Page-Load": "1.50",
    "X-Timing-Render": "3.00",
    "X-Timing-Screenshot": "0.75",
}


def _patch_fetch(**overrides):
    return_value = overrides.pop("return_value", (b"\x89PNG...", _DEFAULT_TIMINGS))
    return patch(
        "commands.screenshot.PiScreenshot.fetch_screenshot",
        new_callable=AsyncMock,
        return_value=return_value,
        **overrides,
    )


def test_sends_file_on_success():
    interaction = _make_interaction()

    with (
        patch(
            "commands.screenshot.http_session.get_session",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        _patch_fetch(),
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
        _patch_fetch(),
    ):
        _run(interaction)

    interaction.response.defer.assert_called_once()


def test_sends_timing_breakdown_as_message_content():
    interaction = _make_interaction()

    with (
        patch(
            "commands.screenshot.http_session.get_session",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        _patch_fetch(),
    ):
        _run(interaction)

    _, kwargs = interaction.followup.send.call_args
    content = kwargs["content"]
    assert "Warmup: 2.00s" in content
    assert "Page Load: 1.50s" in content
    assert "Render: 3.00s" in content
    assert "Screenshot: 0.75s" in content


def test_format_timings_turns_headers_into_readable_lines():
    text = _format_timings({"X-Timing-Warmup": "2.00", "X-Timing-Page-Load": "1.50"})

    assert text == "Warmup: 2.00s\nPage Load: 1.50s"


def test_format_timings_handles_no_timings():
    assert _format_timings({}) == ""


def _run_diff(
    interaction, game="abc-123", objective_id="obj-1", old="old value", new="new value"
):
    import commands.screenshot as screenshot_mod

    with (
        patch.object(screenshot_mod, "client", create=True, new=MagicMock()),
        patch("commands.screenshot.hm.log_command", new_callable=AsyncMock),
    ):
        asyncio.run(get_diff_screenshot(interaction, game, objective_id, old, new))


def test_diff_sends_file_on_success():
    interaction = _make_interaction()

    with (
        patch(
            "commands.screenshot.http_session.get_session",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "commands.screenshot.PiScreenshot.fetch_diff_screenshot",
            new_callable=AsyncMock,
            return_value=(b"\x89PNG...", _DEFAULT_TIMINGS),
        ),
    ):
        _run_diff(interaction)

    interaction.followup.send.assert_called_once()
    _, kwargs = interaction.followup.send.call_args
    assert "file" in kwargs
    assert kwargs["file"].filename == "obj-1-diff.png"


def test_diff_sends_error_message_on_failure():
    from Modules.PiScreenshot import ScreenshotError

    interaction = _make_interaction()

    with (
        patch(
            "commands.screenshot.http_session.get_session",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "commands.screenshot.PiScreenshot.fetch_diff_screenshot",
            new_callable=AsyncMock,
            side_effect=ScreenshotError("404: objective not found"),
        ),
    ):
        _run_diff(interaction)

    msg = interaction.followup.send.call_args[0][0]
    assert "404: objective not found" in msg

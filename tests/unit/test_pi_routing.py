from pi_screenshot_service.routing import build_response, parse_game_id


# ── parse_game_id ───────────────────────────────────────────────────────


def test_parse_game_id_extracts_id_from_valid_path():
    assert parse_game_id("/screenshot/abc-123") == "abc-123"


def test_parse_game_id_returns_none_for_root_path():
    assert parse_game_id("/") is None


def test_parse_game_id_returns_none_when_id_is_missing():
    assert parse_game_id("/screenshot/") is None


def test_parse_game_id_returns_none_for_unrelated_path():
    assert parse_game_id("/healthz") is None


# ── build_response ──────────────────────────────────────────────────────


def test_build_response_returns_400_when_game_id_missing():
    status, content_type, body, headers = build_response(
        None, capture=lambda game_id: (b"", {})
    )

    assert status == 400


def test_build_response_returns_image_png_on_success():
    status, content_type, body, headers = build_response(
        "abc-123", capture=lambda game_id: (b"\x89PNG...", {})
    )

    assert (status, content_type, body) == (200, "image/png", b"\x89PNG...")


def test_build_response_passes_game_id_to_capture():
    received = []

    def capture(game_id: str):
        received.append(game_id)
        return b"", {}

    build_response("abc-123", capture=capture)

    assert received == ["abc-123"]


def test_build_response_returns_504_on_timeout():
    def capture(game_id: str):
        raise TimeoutError("too slow")

    status, content_type, body, headers = build_response("abc-123", capture=capture)

    assert status == 504


def test_build_response_returns_500_on_unexpected_error():
    def capture(game_id: str):
        raise ValueError("boom")

    status, content_type, body, headers = build_response("abc-123", capture=capture)

    assert status == 500


def test_build_response_includes_timing_headers_on_success():
    timings = {"warmup": 2.001, "page_load": 1.5, "render": 3.0, "screenshot": 0.75}

    status, content_type, body, headers = build_response(
        "abc-123", capture=lambda game_id: (b"\x89PNG...", timings)
    )

    assert headers == {
        "X-Timing-Warmup": "2.00",
        "X-Timing-Page-Load": "1.50",
        "X-Timing-Render": "3.00",
        "X-Timing-Screenshot": "0.75",
    }


def test_build_response_has_no_timing_headers_on_error():
    def capture(game_id: str):
        raise TimeoutError("too slow")

    status, content_type, body, headers = build_response("abc-123", capture=capture)

    assert headers == {}

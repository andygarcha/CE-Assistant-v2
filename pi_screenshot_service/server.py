import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pi_screenshot_service.capture import build_driver, capture_game_screenshot
from pi_screenshot_service.routing import build_response, parse_game_id
from pi_screenshot_service.timeout_runner import run_with_timeout

logger = logging.getLogger(__name__)

PORT = 8731
CAPTURE_TIMEOUT_SECONDS = 30

# Only one Selenium/Chrome instance runs at a time: the Pi doesn't have the
# memory headroom for concurrent headless-browser sessions, and screenshots
# aren't latency-sensitive enough to need it.
_capture_lock = threading.Lock()


def _capture(game_id: str) -> tuple[bytes, dict[str, float]]:
    with _capture_lock:
        driver = build_driver()
        return run_with_timeout(
            lambda: capture_game_screenshot(driver, game_id),
            timeout_seconds=CAPTURE_TIMEOUT_SECONDS,
            cleanup=driver.quit,
        )


class ScreenshotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        game_id = parse_game_id(self.path)
        status, content_type, body, headers = build_response(game_id, capture=_capture)

        if status != 200:
            logger.warning("request for %s failed: %s", self.path, body)

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)


def run():
    logging.basicConfig(level=logging.INFO)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ScreenshotHandler)
    logger.info("Listening on port %d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    run()

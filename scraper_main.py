import asyncio
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

for name in ["httpx", "httpcore", "postgrest", "supabase", "urllib3"]:
    logging.getLogger(name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from Modules import SupabaseReader, http_session  # noqa: E402
from web_scraper.scraper import process_loop  # noqa: E402

LOOP_INTERVAL_SECONDS = 1800  # 30 minutes

_shutdown = False


def _handle_signal(sig, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down after current loop...", sig)
    _shutdown = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


async def main():
    logger.info("Scraper starting. Loop interval: %ds", LOOP_INTERVAL_SECONDS)

    try:
        while not _shutdown:
            try:
                SupabaseReader.cleanup_delivered_updates()
                await process_loop()
            except Exception:
                logger.exception("process_loop failed")

            if _shutdown:
                break

            logger.info("Sleeping %ds until next loop...", LOOP_INTERVAL_SECONDS)
            await asyncio.sleep(LOOP_INTERVAL_SECONDS)
    finally:
        await http_session.close_session()
        logger.info("Scraper shut down.")


if __name__ == "__main__":
    asyncio.run(main())

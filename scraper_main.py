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
            # Check loop lock
            if SupabaseReader.is_loop_running():
                logger.warning("Another loop is still running. Skipping this iteration.")
                await asyncio.sleep(LOOP_INTERVAL_SECONDS)
                continue

            # Cleanup old data
            SupabaseReader.cleanup_delivered_updates()
            SupabaseReader.cleanup_completed_commands()

            # Check for pending commands
            commands = SupabaseReader.get_pending_commands()
            full_scrape = False
            for cmd in commands:
                SupabaseReader.acknowledge_command(cmd["id"])
                if cmd["command"] == "full_scrape":
                    full_scrape = True
                SupabaseReader.complete_command(cmd["id"])

            # Acquire loop lock
            run_id = SupabaseReader.start_loop_run()
            try:
                await process_loop(full_scrape=full_scrape)
            except Exception:
                logger.exception("process_loop failed")
            finally:
                SupabaseReader.finish_loop_run(run_id)

            if _shutdown:
                break

            logger.info("Sleeping %ds until next loop...", LOOP_INTERVAL_SECONDS)
            await asyncio.sleep(LOOP_INTERVAL_SECONDS)
    finally:
        await http_session.close_session()
        logger.info("Scraper shut down.")


if __name__ == "__main__":
    asyncio.run(main())

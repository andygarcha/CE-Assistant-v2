import asyncio
import logging
import signal

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
_sleep_task: asyncio.Task | None = None


def _handle_signal(sig, frame):
    global _shutdown
    if _shutdown:
        logger.info("Received signal %s again, forcing exit.", sig)
        raise SystemExit(1)
    logger.info("Received signal %s, shutting down after current loop...", sig)
    _shutdown = True
    if _sleep_task is not None and not _sleep_task.done():
        _sleep_task.cancel()


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


async def main():
    global _sleep_task
    logger.info("Scraper starting. Loop interval: %ds", LOOP_INTERVAL_SECONDS)

    try:
        while not _shutdown:
            # Check loop lock — if a previous loop crashed, run a
            # recovery pass that heals the DB but suppresses notifications.
            recovering = SupabaseReader.is_loop_running()
            if recovering:
                logger.warning(
                    "Previous loop did not finish cleanly. "
                    "Running recovery pass (updates will not be sent)."
                )

            # Cleanup old data
            SupabaseReader.cleanup_delivered_updates()
            SupabaseReader.cleanup_completed_commands()

            # Check for pending commands (skip during recovery)
            full_scrape = False
            if not recovering:
                commands = SupabaseReader.get_pending_commands()
                for cmd in commands:
                    SupabaseReader.acknowledge_command(cmd["id"])
                    if cmd["command"] == "full_scrape":
                        full_scrape = True
                    SupabaseReader.complete_command(cmd["id"])

            # Acquire loop lock
            run_id = SupabaseReader.start_loop_run()
            try:
                result = await process_loop(
                    full_scrape=full_scrape,
                    send_updates=not recovering,
                )
            except Exception:
                logger.exception("process_loop failed")
                result = None
            finally:
                SupabaseReader.finish_loop_run(run_id)

            if recovering and result is not None:
                summary = (
                    f"Recovery scrape completed: "
                    f"{result['games_updated']} games, "
                    f"{result['users_updated']} users, "
                    f"{result['rolls_updated']} rolls updated. "
                    f"{result['updates_generated']} notifications suppressed "
                    f"due to previous failed scrape."
                )
                logger.info(summary)
                SupabaseReader.write_scraper_update(
                    {
                        "is_embed": False,
                        "channel": "privatelog",
                        "text": summary,
                        "title": "",
                        "description": "",
                        "image": "",
                        "url": "",
                        "color": 0,
                        "status": "stable",
                        "game_ce_id": None,
                    }
                )

            if _shutdown:
                break

            logger.info("Sleeping %ds until next loop...", LOOP_INTERVAL_SECONDS)
            _sleep_task = asyncio.ensure_future(asyncio.sleep(LOOP_INTERVAL_SECONDS))
            try:
                await _sleep_task
            except asyncio.CancelledError:
                logger.info("Sleep interrupted by shutdown signal.")
            _sleep_task = None
    finally:
        await http_session.close_session()
        logger.info("Scraper shut down.")


if __name__ == "__main__":
    asyncio.run(main())

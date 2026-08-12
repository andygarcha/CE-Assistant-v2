import datetime
import logging

import discord

from Modules import SupabaseReader, hm

logger = logging.getLogger(__name__)

DISCORD_EMBED_DESCRIPTION_LIMIT = 4096
TRUNCATION_SUFFIX = "\n\n*(truncated)*"


def _truncate_description(description: str) -> str:
    if len(description) <= DISCORD_EMBED_DESCRIPTION_LIMIT:
        return description
    cutoff = DISCORD_EMBED_DESCRIPTION_LIMIT - len(TRUNCATION_SUFFIX)
    return description[:cutoff] + TRUNCATION_SUFFIX


def _format_not_ready_list(not_ready_updates: list[dict]) -> str:
    suffix = ""
    for _update in not_ready_updates:
        suffix += f"\n- [{_update['title']}](<{_update['url']}>)"
    return suffix


async def deliver_updates(client: discord.Client) -> int:
    last_run = SupabaseReader.get_last_loop(offset=False)
    ts = int(last_run.timestamp())
    if datetime.datetime.now(datetime.UTC) - last_run > datetime.timedelta(hours=1):
        check_msg = f":mag: Checking, last scraper loop at <t:{ts}:f> (<t:{ts}:R>)."
        check_msg += "\n:warning: Last scraper loop was more than an hour ago!"
        logger.info("Checking, last scraper loop at %s.", last_run)
        await hm.send_message(client, "privatelog", check_msg, False)

    updates = SupabaseReader.get_stable_updates()
    not_ready_updates = SupabaseReader.get_pending_game_updates()
    not_ready = len(not_ready_updates)

    if not updates:
        if not_ready:
            msg = (
                f":information_source: Nothing stable to send yet ({not_ready} not ready yet)."
                f"{_format_not_ready_list(not_ready_updates)}"
            )
            logger.info(msg)
            await hm.send_message(client, "privatelog", msg, False)
        return 0

    msg = (
        f":information_source: Sending {len(updates)} "
        f"message{'' if len(updates) == 1 else 's'} ({not_ready} not ready yet)."
        f"{_format_not_ready_list(not_ready_updates)}"
    )
    logger.info(msg)
    await hm.send_message(client, "privatelog", msg, False)

    delivered = 0

    for update in updates:
        channel = update["channel"]

        if not update["is_embed"]:
            sent = await hm.send_message(
                client, channel, update["text"], update.get("allowed_mentions") or []
            )
        else:
            embed = discord.Embed()
            embed.title = update["title"]
            embed.description = _truncate_description(update["description"])
            embed.color = update["color"]
            embed.url = update["url"]
            if update["image"]:
                embed.set_image(url=update["image"])
            else:
                embed.set_image(url=hm.SCREENSHOT_FAILED_IMAGE)
            embed.timestamp = datetime.datetime.now(datetime.UTC)
            embed.set_author(name="Challenge Enthusiasts", icon_url=hm.CE_MOUNTAIN_ICON)
            embed.set_footer(text="CE Assistant", icon_url=hm.FINAL_CE_ICON)
            sent = await hm.send_message(client, channel, embed=embed)

        if sent:
            SupabaseReader.mark_updates_delivered([update["id"]])
            delivered += 1
        else:
            logger.warning(
                "Failed to send update %s to %s, will retry next cycle.",
                update["id"],
                channel,
            )

    if delivered:
        logger.info("Delivered %d updates.", delivered)
    return delivered

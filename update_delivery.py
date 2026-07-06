import datetime
import logging

import discord

from Modules import SupabaseReader, hm

logger = logging.getLogger(__name__)


async def deliver_updates(client: discord.Client) -> int:
    last_run = SupabaseReader.get_last_loop(offset=False)
    ts = int(last_run.timestamp())
    if datetime.datetime.now(datetime.timezone.utc) - last_run > datetime.timedelta(
        hours=1
    ):
        check_msg = f":mag: Checking, last scraper loop at <t:{ts}:f> (<t:{ts}:R>)."
        check_msg += "\n:warning: Last scraper loop was more than an hour ago!"
        logger.info("Checking, last scraper loop at %s.", last_run)
        await hm.send_message(client, "privatelog", check_msg, False)

    updates = SupabaseReader.get_stable_updates()
    not_ready = len(SupabaseReader.get_pending_game_updates())

    if not updates:
        if not_ready:
            msg = f":information_source: Nothing stable to send yet ({not_ready} not ready yet)."
            logger.info(msg)
            await hm.send_message(client, "privatelog", msg, False)
        return 0

    msg = (
        f":information_source: Sending {len(updates)} "
        f"message{'' if len(updates) == 1 else 's'} ({not_ready} not ready yet)."
    )
    logger.info(msg)
    await hm.send_message(client, "privatelog", msg, False)

    delivered = 0

    for update in updates:
        channel = update["channel"]

        if not update["is_embed"]:
            sent = await hm.send_message(client, channel, update["text"], False)
        else:
            embed = discord.Embed()
            embed.title = update["title"]
            embed.description = update["description"]
            embed.color = update["color"]
            embed.url = update["url"]
            if update["image"]:
                embed.set_image(url=update["image"])
            else:
                embed.set_image(url=hm.SCREENSHOT_FAILED_IMAGE)
            embed.timestamp = datetime.datetime.now()
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

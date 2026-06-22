import datetime
import logging

import discord

from Modules import SupabaseReader, hm

logger = logging.getLogger(__name__)


async def deliver_updates(client: discord.Client) -> int:
    updates = SupabaseReader.get_stable_updates()
    if not updates:
        return 0

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
            logger.warning("Failed to send update %s to %s, will retry next cycle.", update["id"], channel)

    if delivered:
        logger.info("Delivered %d updates.", delivered)
    return delivered

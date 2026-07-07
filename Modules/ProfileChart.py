"""Generates the /profile completions chart: two bar-chart panels (Tiers,
Categories) rendered as a single PNG, with cached Discord emoji images
pasted below each bar instead of text labels."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

import Modules.hm as hm

from utils.emoji_cache import get_cached_emoji_path

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from Classes.CE_User import CEAPIUser

TIER_ORDER = ["Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"]
CATEGORY_ORDER = [
    "Action",
    "Arcade",
    "Bullet Hell",
    "First-Person",
    "Platformer",
    "Strategy",
]

_TIER_FIELD_NAMES = ["tier1", "tier2", "tier3", "tier4", "tier5"]

# ------------- layout constants -------------
IMAGE_WIDTH = 800
TOP_MARGIN = 20
TITLE_HEIGHT = 30
BAR_AREA_HEIGHT = 150
EMOJI_SIZE = 40
EMOJI_MARGIN = 10
PANEL_HEIGHT = TITLE_HEIGHT + BAR_AREA_HEIGHT + EMOJI_MARGIN + EMOJI_SIZE
PANEL_GAP = 20
IMAGE_HEIGHT = TOP_MARGIN + PANEL_HEIGHT + PANEL_GAP + PANEL_HEIGHT + TOP_MARGIN

BAR_MAX_WIDTH = 70
COUNT_TEXT_GAP = 22

# ------------- color constants -------------
BACKGROUND_COLOR = (17, 17, 17)
TEXT_COLOR = (240, 240, 240)
CATEGORY_BAR_COLOR = (222, 222, 222)
TIER_COLORS = {
    "Tier 1": (0, 188, 99),
    "Tier 2": (228, 177, 1),
    "Tier 3": (228, 114, 13),
    "Tier 4": (230, 68, 52),
    "Tier 5": (169, 5, 177),
}


def tier_counts(api_user: "CEAPIUser") -> list[tuple[str, int]]:
    """Returns [("Tier 1", n), ..., ("Tier 5", n)] from the Total row of
    `api_user.api_tier_summary`. All tiers default to 0 if no Total row exists."""
    for row in api_user.api_tier_summary:
        if hm.genre_id_to_name(row["genreId"]) == "Total":
            return [
                (label, row[field])
                for label, field in zip(TIER_ORDER, _TIER_FIELD_NAMES)
            ]
    return [(label, 0) for label in TIER_ORDER]


def category_counts(api_user: "CEAPIUser") -> list[tuple[str, int]]:
    """Returns [("Action", n), ..., ("Strategy", n)] in fixed alphabetical
    order from `api_user.api_tier_summary`. Missing categories default to 0."""
    totals = {label: 0 for label in CATEGORY_ORDER}
    for row in api_user.api_tier_summary:
        genre_name = hm.genre_id_to_name(row["genreId"])
        if genre_name in totals:
            totals[genre_name] = row["total"]
        elif genre_name != "Total":
            logger.warning(
                "Unknown genreId %r (resolved name %r) encountered while "
                "computing category counts; skipping row",
                row["genreId"],
                genre_name,
            )
    return [(label, totals[label]) for label in CATEGORY_ORDER]


async def _emoji_paths_for(labels: list[str]):
    async def _fetch(label: str):
        markup = hm.get_emoji(label)  # type: ignore
        try:
            return await get_cached_emoji_path(markup)
        except Exception:
            logger.exception("Failed to fetch cached emoji path for label %r", label)
            return None

    return await asyncio.gather(*(_fetch(label) for label in labels))


def _draw_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    title: str,
    entries: list[tuple[str, int]],
    colors: list[tuple[int, int, int]],
    emoji_paths: list,
    top_y: int,
) -> None:
    font_title = ImageFont.load_default(size=20)
    font_count = ImageFont.load_default(size=16)

    draw.text((TOP_MARGIN, top_y), title, font=font_title, fill=TEXT_COLOR)

    axis_y = top_y + TITLE_HEIGHT + BAR_AREA_HEIGHT
    n = len(entries)
    slot_width = IMAGE_WIDTH / n
    bar_width = min(BAR_MAX_WIDTH, slot_width * 0.6)
    max_count = max((count for _, count in entries), default=0) or 1

    for i, (_, count) in enumerate(entries):
        slot_center = slot_width * i + slot_width / 2
        bar_height = round((count / max_count) * BAR_AREA_HEIGHT) if count else 0
        bar_top = axis_y - bar_height

        if bar_height > 0:
            draw.rectangle(
                [
                    slot_center - bar_width / 2,
                    bar_top,
                    slot_center + bar_width / 2,
                    axis_y,
                ],
                fill=colors[i],
            )

        count_text = str(count)
        text_width = draw.textlength(count_text, font=font_count)
        draw.text(
            (slot_center - text_width / 2, bar_top - COUNT_TEXT_GAP),
            count_text,
            font=font_count,
            fill=TEXT_COLOR,
        )

        emoji_path = emoji_paths[i]
        if emoji_path is not None:
            try:
                emoji_image = (
                    Image.open(emoji_path).convert("RGBA").resize((EMOJI_SIZE, EMOJI_SIZE))
                )
                paste_x = round(slot_center - EMOJI_SIZE / 2)
                paste_y = axis_y + EMOJI_MARGIN
                image.paste(emoji_image, (paste_x, paste_y), emoji_image)
            except Exception:
                logger.exception("Failed to paste emoji from path %r", emoji_path)


def _render_image(
    tiers: list[tuple[str, int]],
    categories: list[tuple[str, int]],
    tier_colors: list[tuple[int, int, int]],
    category_colors: list[tuple[int, int, int]],
    tier_emoji_paths: list,
    category_emoji_paths: list,
) -> io.BytesIO:
    """Synchronous Pillow rendering work (image creation, panel drawing,
    PNG encoding). Meant to be run off the event loop via asyncio.to_thread."""
    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    _draw_panel(
        image, draw, "Tiers", tiers, tier_colors, tier_emoji_paths, TOP_MARGIN
    )
    _draw_panel(
        image,
        draw,
        "Categories",
        categories,
        category_colors,
        category_emoji_paths,
        TOP_MARGIN + PANEL_HEIGHT + PANEL_GAP,
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


async def generate_completions_chart(api_user: "CEAPIUser") -> io.BytesIO:
    """Renders the Tiers + Categories completions bar chart and returns a
    PNG-encoded BytesIO buffer ready for Discord upload."""
    tiers = tier_counts(api_user)
    categories = category_counts(api_user)

    tier_colors = [TIER_COLORS[label] for label, _ in tiers]
    category_colors = [CATEGORY_BAR_COLOR for _ in categories]

    tier_emoji_paths = await _emoji_paths_for([label for label, _ in tiers])
    category_emoji_paths = await _emoji_paths_for([label for label, _ in categories])

    return await asyncio.to_thread(
        _render_image,
        tiers,
        categories,
        tier_colors,
        category_colors,
        tier_emoji_paths,
        category_emoji_paths,
    )

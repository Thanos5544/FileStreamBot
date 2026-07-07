import os
import io
import re
import uuid
import time
import aiohttp
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

DEFAULT_BRANDING = "@Patrick_Botz"
DEFAULT_CHANNEL = "@Patrick_Botz"
DEFAULT_CAPTION = "<b>{title} ({year})</b>\n\n➡ <b>Audio:</b> <code>Hindi</code>\n➡ <b>Quality:</b> <code>480p, 720p, 1080p</code>\n➡ <b>Genres:</b> <code>{genres}</code>"
DEFAULT_CAPTION_HINDI = "<b>{title} ({year})</b>\n\n➡ <b>ऑडियो:</b> <code>हिंदी</code>\n➡ <b>क्वालिटी:</b> <code>480p, 720p, 1080p</code>\n➡ <b>शैली:</b> <code>{genres}</code>"

DEFAULT_BUTTONS = [
    {"text": "🔽 480p", "url": "https://t.me/Patrick_Botz"},
    {"text": "🔽 720p", "url": "https://t.me/Patrick_Botz"},
    {"text": "🔽 1080p", "url": "https://t.me/Patrick_Botz"},
    {"text": "📢 Channel", "url": "https://t.me/Patrick_Botz"},
]

COLORS = {
    "red": (231, 76, 60), "orange": (230, 126, 34),
    "yellow": (241, 196, 15), "green": (46, 204, 113),
    "blue": (52, 152, 219), "purple": (155, 89, 182),
    "black": (30, 30, 30),
}

POST_CACHE = {}
USER_SETTINGS = {}


def cb_starts(prefix):
    return filters.create(lambda _, __, q: bool(q.data and q.data.startswith(prefix)))


def cleanup_cache():
    now = time.time()
    for token in list(POST_CACHE.keys()):
        if now - POST_CACHE[token].get("time", now) > 1800:
            POST_CACHE.pop(token, None)


def get_user_settings(user_id):
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {
            "branding": DEFAULT_BRANDING,
            "channel": DEFAULT_CHANNEL,
            "caption": DEFAULT_CAPTION,
            "buttons": DEFAULT_BUTTONS.copy(),
        }
    return USER_SETTINGS[user_id]


async def search_movie(query, year=None, lang="en"):
    async with aiohttp.ClientSession() as s:
        p = {"api_key": TMDB_API, "query": query, "language": lang}
        if year:
            p["year"] = year
        async with s.get(f"{TMDB_BASE}/search/multi", params=p) as r:
            d = await r.json()
            return [x for x in d.get("results", []) if x.get("media_type") in ["movie", "tv"]]


async def get_details(mid, mtype, lang="en"):
    async with aiohttp.ClientSession() as s:
        p = {"api_key": TMDB_API, "append_to_response": "credits", "language": lang}
        async with s.get(f"{TMDB_BASE}/{mtype}/{mid}", params=p) as r:
            return await r.json()


async def get_images(mid, mtype):
    async with aiohttp.ClientSession() as s:
        p = {"api_key": TMDB_API, "include_image_language": "en,null,hi"}
        async with s.get(f"{TMDB_BASE}/{mtype}/{mid}/images", params=p) as r:
            return await r.json()


async def download_image(url):
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
            return await r.read()


def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()


def create_left_gradient(size, color_rgb=None):
    g = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    w, h = size
    for x in range(w):
        alpha = max(0, min(255, int(255 * (1 - x / (w * 0.55)))))
        if color_rgb:
            r, g_c, b = color_rgb
            d.line([(x, 0), (x, h)], fill=(r, g_c, b, alpha))
        else:
            d.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha))
    return g


def create_dark_overlay(size, opacity=90):
    return Image.new("RGBA", size, (0, 0, 0, opacity))

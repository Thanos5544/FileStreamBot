import os
import re
import json
import time
import uuid
import asyncio
import aiohttp
from io import BytesIO
from pathlib import Path

from pyrogram import Client, filters, StopPropagation
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)
from pyrogram.enums import ChatType

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ================== CONFIG ==================
TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "post_settings.json"
FONT_DIR = Path("fonts")
FONT_DIR.mkdir(exist_ok=True)

POST_CACHE = {}
USER_STATE = {}
CACHE_TIME = 1800

# 8 Colours (emoji → RGB)
COLOURS = {
    "🔴": (220, 38, 38),
    "🟠": (234, 88, 12),
    "🟡": (234, 179, 8),
    "🟢": (22, 163, 74),
    "🔵": (37, 99, 235),
    "🟣": (147, 51, 234),
    "⚫": (30, 30, 30),
    "⚪": (240, 240, 240),
}

DEFAULT_SETTINGS = {
    "audio": "Hindi",
    "pixels": "480p | 720p | 1080p",
    "buttons": [],
    "caption_template": """{title} ({year})
╭───────────────────
 ➥ Status: {status}
 ➥ Episodes: {episodes}
 ➥ Ratings: {rating} IMDb
 ➥ Pixels: {pixels}
 ➥ Audio: {audio}
├───────────────────
 ➥ Genres: {genres}
╰───────────────────
≡ {story}"""
}


# ================== HELPERS ==================
def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_SETTINGS.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cleanup_cache():
    now = time.time()
    for token in list(POST_CACHE.keys()):
        if now - POST_CACHE[token].get("time", now) > CACHE_TIME:
            POST_CACHE.pop(token, None)


def cb_starts(prefix: str):
    return filters.create(
        lambda _, __, q: bool(q.data and q.data.startswith(prefix))
    )


def ensure_fonts():
    fonts = {
        "Montserrat-Bold.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
        "Montserrat-Regular.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf",
        "Montserrat-SemiBold.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-SemiBold.ttf",
    }
    for name, url in fonts.items():
        path = FONT_DIR / name
        if not path.exists():
            try:
                import urllib.request
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"Font download failed {name}: {e}")


def get_font(size, bold=False, semi=False):
    ensure_fonts()
    try:
        if bold:
            return ImageFont.truetype(str(FONT_DIR / "Montserrat-Bold.ttf"), size)
        if semi:
            return ImageFont.truetype(str(FONT_DIR / "Montserrat-SemiBold.ttf"), size)
        return ImageFont.truetype(str(FONT_DIR / "Montserrat-Regular.ttf"), size)
    except Exception:
        return ImageFont.load_default()


def tmdb_img_url(path):
    if not path:
        return None
    return TMDB_IMG + path


def get_title(item):
    return (
        item.get("title")
        or item.get("name")
        or item.get("original_title")
        or item.get("original_name")
        or "Unknown"
    )


def get_year(item):
    date = item.get("release_date") or item.get("first_air_date") or ""
    return date[:4] if len(date) >= 4 else "N/A"


# ================== TMDB ==================
async def search_tmdb(session, query):
    async with session.get(
        f"{TMDB_BASE}/search/multi",
        params={"api_key": TMDB_API, "query": query}
    ) as resp:
        return await resp.json()


async def get_details(session, media_type, media_id):
    async with session.get(
        f"{TMDB_BASE}/{media_type}/{media_id}",
        params={"api_key": TMDB_API, "language": "en-US"}
    ) as resp:
        return await resp.json()


async def get_images(session, media_type, media_id):
    async with session.get(
        f"{TMDB_BASE}/{media_type}/{media_id}/images",
        params={"api_key": TMDB_API, "include_image_language": "en,hi,null"}
    ) as resp:
        return await resp.json()


def select_best(results, year=None):
    filtered = [x for x in results if x.get("media_type") in ("movie", "tv")]
    if not filtered:
        return None
    if year:
        for x in filtered:
            d = x.get("release_date") or x.get("first_air_date") or ""
            if d.startswith(year):
                return x
    return filtered[0]


# ================== IMAGE GENERATOR (Pillow) ==================
async def download_image(session, url):
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(BytesIO(data)).convert("RGB")
    except Exception as e:
        print("Image download error:", e)
    return None


def create_gradient_overlay(size, color, opacity=160):
    w, h = size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x in range(w // 2 + 100):
        alpha = int(opacity * (1 - x / (w // 2 + 100)))
        draw.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha))
    for y in range(h // 3):
        alpha = int(80 * (y / (h // 3)))
        draw.line([(0, h - y), (w, h - y)], fill=(0, 0, 0, alpha))
    return overlay


def generate_poster(base_img: Image.Image, info: dict, accent: tuple):
    W, H = 1280, 720
    img = base_img.copy().resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(0.75)
    img = img.convert("RGBA")

    overlay = create_gradient_overlay((W, H), accent, 190)
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)

    f_title = get_font(54, bold=True)
    f_meta = get_font(26, semi=True)
    f_small = get_font(22)
    f_tiny = get_font(18)

    title = info.get("title", "Unknown")
    year = info.get("year", "")
    rating = info.get("rating", "N/A")
    genres = info.get("genres", "")
    media_type = info.get("media_type", "movie")

    draw.rectangle([0, 0, 12, H], fill=accent + (255,))

    y = 80
    title_lines = []
    words = title.upper().split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=f_title) < 620:
            line = test
        else:
            if line:
                title_lines.append(line)
            line = w
    if line:
        title_lines.append(line)

    for i, ln in enumerate(title_lines[:3]):
        draw.text((50, y + i * 60), ln, font=f_title, fill=(255, 255, 255, 255))

    y += len(title_lines) * 60 + 15

    type_text = "TV SERIES" if media_type == "tv" else "MOVIE"
    draw.text((50, y), f"{year}  •  {type_text}", font=f_meta, fill=(200, 200, 200, 255))
    y += 50

    draw.rectangle([50, y, 280, y + 5], fill=accent + (255,))
    y += 35

    badge_w, badge_h = 160, 42
    draw.rounded_rectangle([50, y, 50 + badge_w, y + badge_h], radius=8, fill=accent + (255,))
    draw.text((50 + 18, y + 8), f"★  {rating} IMDb", font=f_small, fill=(255, 255, 255, 255))
    y += 70

    if genres:
        draw.text((50, y), genres.upper()[:60], font=f_tiny, fill=(180, 180, 180, 255))

    draw.rectangle([0, H - 8, W, H], fill=accent + (255,))

    final = img.convert("RGB")
    bio = BytesIO()
    final.save(bio, format="JPEG", quality=92)
    bio.seek(0)
    return bio


# ================== CAPTION ==================
def build_caption(info: dict, settings: dict):
    template = settings.get("caption_template", DEFAULT_SETTINGS["caption_template"])

    data = {
        "title": info.get("title", "Unknown"),
        "year": info.get("year", "N/A"),
        "status": info.get("status", "—"),
        "episodes": info.get("episodes", "—"),
        "rating": info.get("rating", "N/A"),
        "pixels": settings.get("pixels", "480p | 720p | 1080p"),
        "audio": settings.get("audio", "Hindi"),
        "genres": info.get("genres", "—"),
        "story": info.get("story", "No overview available."),
    }

    caption = template.format(**data)

    if info.get("media_type") == "movie":
        lines = []
        for line in caption.splitlines():
            if "Status:" in line or "Episodes:" in line:
                continue
            lines.append(line)
        caption = "\n".join(lines)

    return caption.strip()


def build_post_keyboard(token, page, total, current_color="🟢"):
    colours = list(COLOURS.keys())
    color_row = []
    for c in colours:
        text = f"•{c}•" if c == current_color else c
        color_row.append(
            InlineKeyboardButton(text, callback_data=f"postcol|{token}|{c}")
        )

    row1 = color_row[:4]
    row2 = color_row[4:]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ PREV", callback_data=f"postpage|{token}|{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="postnoop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("NEXT ➡️", callback_data=f"postpage|{token}|{page+1}"))

    buttons = [row1, row2, nav]

    buttons.append([
        InlineKeyboardButton("🗑 CLEAR", callback_data=f"postclear|{token}")
    ])

    return InlineKeyboardMarkup(buttons)


def build_url_buttons(settings):
    raw = settings.get("buttons", [])
    if not raw:
        return None
    rows = []
    for b in raw:
        if isinstance(b, dict) and b.get("text") and b.get("url"):
            rows.append([InlineKeyboardButton(b["text"], url=b["url"])])
    return InlineKeyboardMarkup(rows) if rows else None
  # ================== COMMAND /post ==================
@Client.on_message(filters.command("post") & filters.private)
async def post_cmd(client: Client, message: Message):
    cleanup_cache()

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n`/post movie or series name`\n\n"
            "Example:\n`/post the witcher`\n`/post pathaan 2023`"
        )

    query = " ".join(message.command[1:]).strip()
    msg = await message.reply_text("🔎 Searching & designing poster...")

    try:
        year = None
        m = re.search(r"(19|20)\d{2}", query)
        if m:
            year = m.group()
            search_q = query.replace(year, "").strip()
        else:
            search_q = query

        async with aiohttp.ClientSession() as session:
            search = await search_tmdb(session, search_q)
            results = search.get("results", [])
            item = select_best(results, year)

            if not item:
                return await msg.edit_text("❌ Kuch nahi mila bro.")

            media_type = item["media_type"]
            media_id = item["id"]

            details = await get_details(session, media_type, media_id)
            images_data = await get_images(session, media_type, media_id)

            posters = []
            if details.get("backdrop_path"):
                posters.append(tmdb_img_url(details["backdrop_path"]))
            if details.get("poster_path"):
                posters.append(tmdb_img_url(details["poster_path"]))

            for p in images_data.get("backdrops", [])[:12]:
                url = tmdb_img_url(p.get("file_path"))
                if url and url not in posters:
                    posters.append(url)
            for p in images_data.get("posters", [])[:8]:
                url = tmdb_img_url(p.get("file_path"))
                if url and url not in posters:
                    posters.append(url)

            if not posters:
                return await msg.edit_text("❌ Images nahi mile.")

            genres = ", ".join([g["name"] for g in details.get("genres", [])][:4]) or "—"
            rating = details.get("vote_average")
            rating = f"{rating:.1f}" if rating else "N/A"

            if media_type == "tv":
                status = details.get("status", "—")
                eps = details.get("number_of_episodes")
                episodes = f"{eps}+" if eps else "—"
            else:
                status = "—"
                episodes = "—"

            story = (details.get("overview") or "No overview available.").strip()
            if len(story) > 280:
                story = story[:277] + "..."

            info = {
                "title": get_title(details),
                "year": get_year(details),
                "rating": rating,
                "genres": genres,
                "status": status,
                "episodes": episodes,
                "story": story,
                "media_type": media_type,
            }

            base = await download_image(session, posters[0])
            if not base:
                return await msg.edit_text("❌ Poster download fail.")

            settings = load_settings()
            accent = COLOURS["🟢"]
            photo = generate_poster(base, info, accent)
            caption = build_caption(info, settings)

            token = uuid.uuid4().hex[:12]
            POST_CACHE[token] = {
                "user_id": message.from_user.id,
                "chat_id": message.chat.id,
                "info": info,
                "posters": posters,
                "page": 0,
                "color": "🟢",
                "base_images": {0: base},
                "time": time.time(),
                "settings": settings,
            }

            kb = build_post_keyboard(token, 0, len(posters), "🟢")

            await msg.delete()
            await client.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=caption,
                reply_markup=kb
            )

    except Exception as e:
        print("POST ERROR:", e)
        await msg.edit_text(f"❌ Error:\n`{str(e)[:800]}`")


# ================== CALLBACKS ==================
@Client.on_callback_query(cb_starts("postcol|"), group=-900)
async def post_color(client: Client, query: CallbackQuery):
    try:
        _, token, color = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            return

        if color not in COLOURS:
            await query.answer("Invalid colour")
            return

        data["color"] = color
        page = data["page"]
        posters = data["posters"]

        if page not in data["base_images"]:
            async with aiohttp.ClientSession() as session:
                img = await download_image(session, posters[page])
                if not img:
                    await query.answer("Image load fail", show_alert=True)
                    return
                data["base_images"][page] = img
        base = data["base_images"][page]

        photo = generate_poster(base, data["info"], COLOURS[color])
        caption = build_caption(data["info"], data["settings"])
        kb = build_post_keyboard(token, page, len(posters), color)

        await query.message.edit_media(
            media=InputMediaPhoto(photo, caption=caption),
            reply_markup=kb
        )
        await query.answer(f"Colour {color}")

    except Exception as e:
        print("COLOR ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postpage|"), group=-900)
async def post_page(client: Client, query: CallbackQuery):
    try:
        _, token, page_s = query.data.split("|")
        page = int(page_s)
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            return

        posters = data["posters"]
        if page < 0 or page >= len(posters):
            await query.answer("No more")
            return

        data["page"] = page
        color = data["color"]

        if page not in data["base_images"]:
            async with aiohttp.ClientSession() as session:
                img = await download_image(session, posters[page])
                if not img:
                    await query.answer("Image load fail", show_alert=True)
                    return
                data["base_images"][page] = img

        base = data["base_images"][page]
        photo = generate_poster(base, data["info"], COLOURS[color])
        caption = build_caption(data["info"], data["settings"])
        kb = build_post_keyboard(token, page, len(posters), color)

        await query.message.edit_media(
            media=InputMediaPhoto(photo, caption=caption),
            reply_markup=kb
        )
        await query.answer(f"Page {page+1}")

    except Exception as e:
        print("PAGE ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postclear|"), group=-900)
async def post_clear(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if data and query.from_user.id != data["user_id"]:
            await query.answer("Not yours", show_alert=True)
            return

        POST_CACHE.pop(token, None)
        await query.message.edit_caption("❌ Cleared.")
        await query.message.edit_reply_markup(reply_markup=None)
        await query.answer("Cleared")
    finally:
        raise StopPropagation


@Client.on_callback_query(filters.regex(r"^postnoop$"), group=-900)
async def post_noop(_, query: CallbackQuery):
    await query.answer()
    raise StopPropagation


# ================== /settings ==================
@Client.on_message(filters.command("settings") & filters.private)
async def settings_cmd(client: Client, message: Message):
    s = load_settings()
    text = (
        "⚙️ **POST SETTINGS**\n\n"
        f"🎧 **Audio:** `{s.get('audio')}`\n"
        f"📺 **Pixels:** `{s.get('pixels')}`\n"
        f"🔘 **Buttons:** `{len(s.get('buttons', []))} buttons`\n\n"
        f"**Caption Template:**\n```\n{s.get('caption_template')[:400]}...\n```"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 CAPTION", callback_data="set_caption"),
            InlineKeyboardButton("🎧 AUDIO", callback_data="set_audio"),
        ],
        [
            InlineKeyboardButton("📺 PIXELS", callback_data="set_pixels"),
            InlineKeyboardButton("🔘 BUTTONS", callback_data="set_buttons"),
        ],
        [
            InlineKeyboardButton("🔄 RESET DEFAULT", callback_data="set_reset"),
        ]
    ])
    await message.reply_text(text, reply_markup=kb)


@Client.on_callback_query(cb_starts("set_"), group=-901)
async def settings_cb(client: Client, query: CallbackQuery):
    action = query.data

    if action == "set_caption":
        USER_STATE[query.from_user.id] = "wait_caption"
        await query.message.reply_text(
            "📝 Naya **caption template** bhej de.\n\n"
            "Placeholders:\n"
            "`{title} {year} {status} {episodes} {rating} {pixels} {audio} {genres} {story}`\n\n"
            "Cancel ke liye /cancel"
        )
        await query.answer()

    elif action == "set_audio":
        USER_STATE[query.from_user.id] = "wait_audio"
        await query.message.reply_text("🎧 Naya default **Audio** bhej (example: Hindi / English / Dual)\n\n/cancel")
        await query.answer()

    elif action == "set_pixels":
        USER_STATE[query.from_user.id] = "wait_pixels"
        await query.message.reply_text("📺 Naya **Pixels** bhej (example: 480p | 720p | 1080p)\n\n/cancel")
        await query.answer()

    elif action == "set_buttons":
        USER_STATE[query.from_user.id] = "wait_buttons"
        await query.message.reply_text(
            "🔘 Buttons set karne ke liye is format me bhej:\n\n"
            "`Button Text - https://link.com`\n"
            "`Another Button - https://t.me/...`\n\n"
            "Har line pe ek button.\n"
            "Clear karne ke liye sirf `clear` likh ke bhej.\n\n/cancel"
        )
        await query.answer()

    elif action == "set_reset":
        save_settings(DEFAULT_SETTINGS.copy())
        await query.answer("Reset done ✅", show_alert=True)
        await query.message.edit_text("✅ Settings reset to default.\n\nDobara /settings kar.")
    raise StopPropagation


@Client.on_message(filters.private & filters.text & ~filters.command(["post", "settings", "cancel", "img"]))
async def settings_input(client: Client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid)
    if not state:
        return

    text = message.text.strip()

    if text.lower() == "/cancel":
        USER_STATE.pop(uid, None)
        return await message.reply_text("❌ Cancelled.")

    s = load_settings()

    if state == "wait_caption":
        s["caption_template"] = text
        save_settings(s)
        USER_STATE.pop(uid, None)
        await message.reply_text("✅ Caption template save ho gaya!")

    elif state == "wait_audio":
        s["audio"] = text
        save_settings(s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ Audio set: `{text}`")

    elif state == "wait_pixels":
        s["pixels"] = text
        save_settings(s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ Pixels set: `{text}`")

    elif state == "wait_buttons":
        if text.lower() == "clear":
            s["buttons"] = []
        else:
            buttons = []
            for line in text.splitlines():
                if " - " in line:
                    parts = line.split(" - ", 1)
                    if len(parts) == 2 and parts[1].startswith("http"):
                        buttons.append({"text": parts[0].strip(), "url": parts[1].strip()})
            s["buttons"] = buttons
        save_settings(s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ {len(s['buttons'])} buttons save ho gaye!")


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_state(_, message: Message):
    USER_STATE.pop(message.from_user.id, None)
    await message.reply_text("✅ State cleared.")

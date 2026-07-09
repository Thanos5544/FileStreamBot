import os
import re
import json
import time
import uuid
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

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

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

COLOURS = {
    "🔴": (220, 38, 38),
    "🟠": (234, 88, 12),
    "🟡": (234, 179, 8),
    "🟢": (22, 163, 74),
    "🔵": (37, 99, 235),
    "🟣": (147, 51, 234),
    "⚫": (24, 24, 24),
    "⚪": (245, 245, 245),
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


async def download_image(session, url):
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(BytesIO(data)).convert("RGB")
    except Exception as e:
        print("Image download error:", e)
    return None


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_poster(base_img: Image.Image, info: dict, accent: tuple):
    """Exact style like screenshots - NO branding"""
    W, H = 1280, 720

    img = base_img.copy().resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(0.68)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = img.convert("RGBA")

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    for x in range(0, 750):
        alpha = int(225 * (1 - x / 750) ** 0.9)
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))

    for y in range(0, 140):
        alpha = int(70 * (1 - y / 140))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

    for y in range(H - 180, H):
        alpha = int(90 * ((y - (H - 180)) / 180))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    f_title = get_font(78, bold=True)
    f_meta = get_font(23, semi=True)
    f_story = get_font(23)
    f_btn = get_font(23, bold=True)

    title = info.get("title", "Unknown").upper()
    year = info.get("year", "")
    rating = info.get("rating", "N/A")
    genres = info.get("genres", "")
    status = info.get("status", "")
    story = info.get("story", "")
    media_type = info.get("media_type", "movie")

    left = 60
    y = 145

    title_lines = wrap_text(title, f_title, 640, draw)[:2]
    for i, line in enumerate(title_lines):
        draw.text((left, y + i * 82), line, font=f_title, fill=(255, 255, 255, 255))
    y += len(title_lines) * 82 + 8

    draw.rectangle([left, y, left + 155, y + 7], fill=accent + (255,))
    y += 32

    meta_parts = []
    if year:
        meta_parts.append(str(year))
    if genres:
        meta_parts.append(genres.upper())
    if media_type == "tv" and status and status not in ["—", ""]:
        meta_parts.append(status.upper())
    meta = "  •  ".join(meta_parts)
    draw.text((left, y), meta[:75], font=f_meta, fill=(200, 200, 200, 255))
    y += 48

    if story:
        story_lines = wrap_text(story, f_story, 620, draw)[:4]
        for i, line in enumerate(story_lines):
            draw.text((left, y + i * 31), line, font=f_story, fill=(185, 185, 185, 255))
        y += len(story_lines) * 31 + 45
    else:
        y += 35

    btn_h = 54
    btn_y = y

    watch_w = 225
    draw.rounded_rectangle(
        [left, btn_y, left + watch_w, btn_y + btn_h],
        radius=12,
        fill=accent + (255,)
    )
    draw.text((left + 22, btn_y + 13), "▶  WATCH NOW", font=f_btn, fill=(255, 255, 255, 255))

    imdb_x = left + watch_w + 16
    imdb_w = 175
    draw.rounded_rectangle(
        [imdb_x, btn_y, imdb_x + imdb_w, btn_y + btn_h],
        radius=12,
        fill=(12, 12, 12, 240)
    )
    draw.rounded_rectangle(
        [imdb_x, btn_y, imdb_x + imdb_w, btn_y + btn_h],
        radius=12,
        outline=(255, 255, 255, 45),
        width=2
    )
    draw.text((imdb_x + 26, btn_y + 13), f"★  {rating} IMDb", font=f_btn, fill=(255, 255, 255, 255))

    final = img.convert("RGB")
    bio = BytesIO()
    final.save(bio, format="JPEG", quality=94)
    bio.seek(0)
    bio.name = "poster.jpg"
    return bio


def make_clean_image(base_img: Image.Image):
    W, H = 1280, 720
    img = base_img.copy().resize((W, H), Image.LANCZOS)
    bio = BytesIO()
    img.save(bio, format="JPEG", quality=94)
    bio.seek(0)
    bio.name = "clean.jpg"
    return bio


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


def build_post_keyboard(token, page, total, current_color="🔴", clean_mode=False):
    colours = list(COLOURS.keys())
    color_btns = []
    for c in colours:
        mark = f"•{c}•" if c == current_color else c
        color_btns.append(InlineKeyboardButton(mark, callback_data=f"postcol|{token}|{c}"))

    row1 = color_btns[:4]
    row2 = color_btns[4:]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ PREV", callback_data=f"postpage|{token}|{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="postnoop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("NEXT ➡️", callback_data=f"postpage|{token}|{page+1}"))

    action_row = [
        InlineKeyboardButton("🖼 CLEAN" if not clean_mode else "🎨 DESIGN", callback_data=f"postclean|{token}"),
        InlineKeyboardButton("✅ USE THIS", callback_data=f"postuse|{token}"),
    ]

    buttons = [row1, row2, nav, action_row, [
        InlineKeyboardButton("🗑 CLEAR", callback_data=f"postclear|{token}")
    ]]
    return InlineKeyboardMarkup(buttons)


def build_url_buttons(settings):
    raw = settings.get("buttons", [])
    rows = []
    for b in raw:
        if isinstance(b, dict) and b.get("text") and b.get("url"):
            rows.append([InlineKeyboardButton(b["text"], url=b["url"])])
    if not rows:
        rows = [[InlineKeyboardButton("No buttons in /settings", callback_data="postnoop")]]
    rows.append([InlineKeyboardButton("🗑 CLEAR", callback_data="postclear|final")])
    return InlineKeyboardMarkup(rows)
    # ================== /post COMMAND ==================
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

            genres = ", ".join([g["name"] for g in details.get("genres", [])][:3]) or "—"
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
            if len(story) > 260:
                story = story[:257] + "..."

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
            photo = generate_poster(base, info, COLOURS["🔴"])
            caption = build_caption(info, settings)

            token = uuid.uuid4().hex[:12]
            POST_CACHE[token] = {
                "user_id": message.from_user.id,
                "chat_id": message.chat.id,
                "info": info,
                "posters": posters,
                "page": 0,
                "color": "🔴",
                "clean_mode": False,
                "base_images": {0: base},
                "time": time.time(),
                "settings": settings,
            }

            kb = build_post_keyboard(token, 0, len(posters), "🔴", False)

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


async def render_and_edit(client, query, data, token):
    page = data["page"]
    color = data["color"]
    posters = data["posters"]
    clean_mode = data.get("clean_mode", False)

    if page not in data["base_images"]:
        async with aiohttp.ClientSession() as session:
            img = await download_image(session, posters[page])
            if not img:
                await query.answer("Image load fail", show_alert=True)
                return
            data["base_images"][page] = img

    base = data["base_images"][page]

    if clean_mode:
        photo = make_clean_image(base)
    else:
        photo = generate_poster(base, data["info"], COLOURS[color])

    caption = build_caption(data["info"], data["settings"])
    kb = build_post_keyboard(token, page, len(posters), color, clean_mode)

    await query.message.edit_media(
        media=InputMediaPhoto(photo, caption=caption),
        reply_markup=kb
    )


@Client.on_callback_query(cb_starts("postcol|"), group=-900)
async def post_color(client: Client, query: CallbackQuery):
    try:
        _, token, color = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            return await query.answer("Expired / not yours", show_alert=True)
        if color not in COLOURS:
            return await query.answer("Invalid")

        data["color"] = color
        data["clean_mode"] = False
        await render_and_edit(client, query, data, token)
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
            return await query.answer("Expired / not yours", show_alert=True)

        if page < 0 or page >= len(data["posters"]):
            return await query.answer("No more")

        data["page"] = page
        await render_and_edit(client, query, data, token)
        await query.answer(f"Page {page+1}")
    except Exception as e:
        print("PAGE ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postclean|"), group=-900)
async def post_clean(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            return await query.answer("Expired / not yours", show_alert=True)

        data["clean_mode"] = not data.get("clean_mode", False)
        await render_and_edit(client, query, data, token)
        await query.answer("Clean" if data["clean_mode"] else "Design")
    except Exception as e:
        print("CLEAN ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postuse|"), group=-900)
async def post_use(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            return await query.answer("Expired / not yours", show_alert=True)

        kb = build_url_buttons(data["settings"])
        await query.message.edit_reply_markup(reply_markup=kb)
        await query.answer("✅ Buttons applied")
    except Exception as e:
        print("USE ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postclear|"), group=-900)
async def post_clear(client: Client, query: CallbackQuery):
    try:
        parts = query.data.split("|")
        token = parts[1] if len(parts) > 1 else None
        if token and token != "final":
            data = POST_CACHE.get(token)
            if data and query.from_user.id != data["user_id"]:
                return await query.answer("Not yours", show_alert=True)
            POST_CACHE.pop(token, None)

        try:
            await query.message.edit_caption("❌ Cleared.")
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
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
        f"**Caption Template:**\n```\n{s.get('caption_template')[:380]}\n```"
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
        [InlineKeyboardButton("🔄 RESET DEFAULT", callback_data="set_reset")]
    ])
    await message.reply_text(text, reply_markup=kb)


@Client.on_callback_query(cb_starts("set_"), group=-901)
async def settings_cb(client: Client, query: CallbackQuery):
    action = query.data
    if action == "set_caption":
        USER_STATE[query.from_user.id] = "wait_caption"
        await query.message.reply_text(
            "📝 Naya **caption template** bhej.\n\n"
            "Placeholders:\n"
            "`{title} {year} {status} {episodes} {rating} {pixels} {audio} {genres} {story}`\n\n"
            "/cancel se cancel"
        )
    elif action == "set_audio":
        USER_STATE[query.from_user.id] = "wait_audio"
        await query.message.reply_text("🎧 Naya Audio bhej (Hindi / English / Dual)\n\n/cancel")
    elif action == "set_pixels":
        USER_STATE[query.from_user.id] = "wait_pixels"
        await query.message.reply_text("📺 Naya Pixels bhej\nExample: `480p | 720p | 1080p`\n\n/cancel")
    elif action == "set_buttons":
        USER_STATE[query.from_user.id] = "wait_buttons"
        await query.message.reply_text(
            "🔘 Format:\n`Button Text - https://link.com`\n"
            "Har line pe ek button.\n"
            "Clear ke liye: `clear`\n\n/cancel"
        )
    elif action == "set_reset":
        save_settings(DEFAULT_SETTINGS.copy())
        await query.answer("Reset done ✅", show_alert=True)
        await query.message.edit_text("✅ Reset ho gaya. Dobara /settings kar.")
    await query.answer()
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
        await message.reply_text("✅ Caption save!")
    elif state == "wait_audio":
        s["audio"] = text
        save_settings(s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ Audio: `{text}`")
    elif state == "wait_pixels":
        s["pixels"] = text
        save_settings(s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ Pixels: `{text}`")
    elif state == "wait_buttons":
        if text.lower() == "clear":
            s["buttons"] = []
        else:
            buttons = []
            for line in text.splitlines():
                if " - " in line:
                    parts = line.split(" - ", 1)
                    if len(parts) == 2 and parts[1].strip().startswith("http"):
                        buttons.append({"text": parts[0].strip(), "url": parts[1].strip()})
            s["buttons"] = buttons
        save_settings(s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ {len(s['buttons'])} buttons save!")


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_state(_, message: Message):
    USER_STATE.pop(message.from_user.id, None)
    await message.reply_text("✅ Cleared.")

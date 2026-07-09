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

TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
ANIME_SETTINGS_FILE = DATA_DIR / "anime_settings.json"
FONT_DIR = Path("fonts")
FONT_DIR.mkdir(exist_ok=True)

ANIME_CACHE = {}
ANIME_STATE = {}
CACHE_TIME = 1800

COLOURS = {
    "🔴": (220, 38, 38),
    "🟠": (234, 88, 12),
    "🟡": (234, 179, 8),
    "🟢": (16, 185, 129),
    "🔵": (37, 99, 235),
    "🟣": (147, 51, 234),
    "⚫": (24, 24, 24),
    "⚪": (245, 245, 245),
}

DEFAULT_ANIME_SETTINGS = {
    "audio": "Japanese | Hindi",
    "pixels": "480p | 720p | 1080p",
    "buttons": [],
    "caption_template": """{title} ({year})
╭───────────────────
 ➥ Type: Anime
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


def load_anime_settings():
    if ANIME_SETTINGS_FILE.exists():
        try:
            with open(ANIME_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_ANIME_SETTINGS.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return DEFAULT_ANIME_SETTINGS.copy()


def save_anime_settings(data):
    with open(ANIME_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cleanup_anime_cache():
    now = time.time()
    for token in list(ANIME_CACHE.keys()):
        if now - ANIME_CACHE[token].get("time", now) > CACHE_TIME:
            ANIME_CACHE.pop(token, None)


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
                print("Font download failed", name, e)


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
        params={"api_key": TMDB_API, "include_image_language": "en,ja,null"}
    ) as resp:
        return await resp.json()


def select_anime(results, year=None):
    # prefer animation / tv
    filtered = []
    for x in results:
        mt = x.get("media_type")
        if mt not in ("movie", "tv"):
            continue
        filtered.append(x)

    if not filtered:
        return None

    # prefer items that look like anime-ish by genre later; first pass year match
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


def generate_anime_poster(base_img, info, accent):
    """
    Anime Soft Glow template
    - soft dark (not heavy movie black)
    - left full colour line
    - soft accent wash
    - clean title + underline
    - soft story
    - WATCH NOW + IMDb (no star)
    - no branding
    """
    W, H = 1280, 720

    img = base_img.copy().resize((W, H), Image.LANCZOS)
    # anime art preserve - less dark than movie template
    img = ImageEnhance.Brightness(img).enhance(0.68)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.12)
    img = img.convert("RGBA")

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    ar, ag, ab = accent

    # soft left wash
    for x in range(0, 760):
        p = (1.0 - (x / 760.0)) ** 0.70
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, int(200 * p)))
        od.line([(x, 0), (x, H)], fill=(ar, ag, ab, int(36 * p)))

    # soft vignette top/bottom
    for y in range(0, 80):
        a = int(35 * (1 - y / 80))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    for y in range(H - 120, H):
        a = int(55 * ((y - (H - 120)) / 120))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, a))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # LEFT FULL COLOUR LINE
    draw.rectangle([0, 0, 10, H], fill=accent + (255,))

    f_title = get_font(74, bold=True)
    f_meta = get_font(21, semi=True)
    f_story = get_font(19)
    f_btn = get_font(21, bold=True)
    f_tag = get_font(16, semi=True)

    title = info.get("title", "Unknown").upper()
    year = info.get("year", "")
    rating = info.get("rating", "N/A")
    genres = info.get("genres", "")
    status = info.get("status", "")
    story = info.get("story", "")

    left = 70
    y = 120

    # small ANIME tag
    draw.rounded_rectangle([left, y, left + 92, y + 28], radius=8, fill=accent + (230,))
    draw.text((left + 16, y + 5), "ANIME", font=f_tag, fill=(255, 255, 255, 255))
    y += 48

    # TITLE
    title_lines = wrap_text(title, f_title, 640, draw)[:2]
    for i, line in enumerate(title_lines):
        ty = y + i * 78
        draw.text((left + 2, ty + 2), line, font=f_title, fill=(0, 0, 0, 100))
        draw.text((left, ty), line, font=f_title, fill=(255, 255, 255, 250))
    y += len(title_lines) * 78 + 12

    # underline (title ke neeche)
    draw.rectangle([left, y, left + 135, y + 6], fill=accent + (255,))
    y += 30

    # meta
    meta_parts = []
    if year:
        meta_parts.append(str(year))
    if genres:
        g = genres.upper()
        parts = [p.strip() for p in g.split(",")]
        if len(parts) >= 2:
            g = f"{parts[0]} & {parts[1]}"
        meta_parts.append(g)
    if status and status not in ["—", ""]:
        st = status.upper()
        if "RETURNING" in st:
            st = "RETURNING"
        meta_parts.append(st)
    meta = "  •  ".join(meta_parts)
    draw.text((left, y), meta[:76], font=f_meta, fill=(205, 205, 205, 230))
    y += 40

    # story soft
    if story:
        story_lines = wrap_text(story, f_story, 500, draw)[:4]
        for i, line in enumerate(story_lines):
            draw.text((left, y + i * 26), line, font=f_story, fill=(185, 185, 185, 165))
        y += len(story_lines) * 26 + 36
    else:
        y += 28

    # buttons
    btn_h = 50
    btn_y = min(y, H - 105)

    watch_w = 210
    draw.rounded_rectangle(
        [left, btn_y, left + watch_w, btn_y + btn_h],
        radius=12,
        fill=accent + (255,)
    )
    draw.text((left + 22, btn_y + 12), "▶  WATCH NOW", font=f_btn, fill=(255, 255, 255, 255))

    imdb_x = left + watch_w + 12
    imdb_w = 150
    draw.rounded_rectangle(
        [imdb_x, btn_y, imdb_x + imdb_w, btn_y + btn_h],
        radius=12,
        fill=(0, 0, 0, 220)
    )
    draw.rounded_rectangle(
        [imdb_x, btn_y, imdb_x + imdb_w, btn_y + btn_h],
        radius=12,
        outline=(255, 255, 255, 70),
        width=2
    )
    draw.text((imdb_x + 28, btn_y + 12), f"{rating} IMDb", font=f_btn, fill=(255, 255, 255, 255))

    final = img.convert("RGB")
    bio = BytesIO()
    final.save(bio, format="JPEG", quality=95)
    bio.seek(0)
    bio.name = "anime.jpg"
    return bio


def make_clean_image(base_img):
    W, H = 1280, 720
    img = base_img.copy().resize((W, H), Image.LANCZOS)
    bio = BytesIO()
    img.save(bio, format="JPEG", quality=95)
    bio.seek(0)
    bio.name = "clean.jpg"
    return bio


def build_anime_caption(info, settings):
    template = settings.get("caption_template", DEFAULT_ANIME_SETTINGS["caption_template"])
    data = {
        "title": info.get("title", "Unknown"),
        "year": info.get("year", "N/A"),
        "status": info.get("status", "—"),
        "episodes": info.get("episodes", "—"),
        "rating": info.get("rating", "N/A"),
        "pixels": settings.get("pixels", "480p | 720p | 1080p"),
        "audio": settings.get("audio", "Japanese | Hindi"),
        "genres": info.get("genres", "—"),
        "story": info.get("story", "No overview available."),
    }
    return template.format(**data).strip()


def build_anime_keyboard(token, page, total, current_color="🟣", clean_mode=False):
    colours = list(COLOURS.keys())
    color_btns = []
    for c in colours:
        mark = f"•{c}•" if c == current_color else c
        color_btns.append(InlineKeyboardButton(mark, callback_data=f"anicol|{token}|{c}"))

    row1 = color_btns[:4]
    row2 = color_btns[4:]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ PREV", callback_data=f"anipage|{token}|{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="aninoop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("NEXT ➡️", callback_data=f"anipage|{token}|{page+1}"))

    action_row = [
        InlineKeyboardButton("🖼 CLEAN" if not clean_mode else "🎨 DESIGN", callback_data=f"aniclean|{token}"),
        InlineKeyboardButton("✅ USE THIS", callback_data=f"aniuse|{token}"),
    ]

    buttons = [row1, row2, nav, action_row, [
        InlineKeyboardButton("🗑 CLEAR", callback_data=f"aniclear|{token}")
    ]]
    return InlineKeyboardMarkup(buttons)


def build_anime_url_buttons(settings):
    raw = settings.get("buttons", [])
    rows = []
    for b in raw:
        if isinstance(b, dict) and b.get("text") and b.get("url"):
            rows.append([InlineKeyboardButton(b["text"], url=b["url"])])
    if not rows:
        rows = [[InlineKeyboardButton("No buttons in /animesettings", callback_data="aninoop")]]
    rows.append([InlineKeyboardButton("🗑 CLEAR", callback_data="aniclear|final")])
    return InlineKeyboardMarkup(rows)

@Client.on_message(filters.command("anime") & filters.private)
async def anime_cmd(client: Client, message: Message):
    cleanup_anime_cache()

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n`/anime anime name`\n\n"
            "Example:\n`/anime naruto`\n`/anime demon slayer 2019`"
        )

    query = " ".join(message.command[1:]).strip()
    msg = await message.reply_text("🔎 Searching anime & designing poster...")

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
            item = select_anime(results, year)

            if not item:
                return await msg.edit_text("❌ Anime nahi mila bro.")

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
            if len(story) > 220:
                story = story[:217] + "..."

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

            settings = load_anime_settings()
            photo = generate_anime_poster(base, info, COLOURS["🟣"])
            caption = build_anime_caption(info, settings)

            token = uuid.uuid4().hex[:12]
            ANIME_CACHE[token] = {
                "user_id": message.from_user.id,
                "chat_id": message.chat.id,
                "info": info,
                "posters": posters,
                "page": 0,
                "color": "🟣",
                "clean_mode": False,
                "base_images": {0: base},
                "time": time.time(),
                "settings": settings,
            }

            kb = build_anime_keyboard(token, 0, len(posters), "🟣", False)
            await msg.delete()
            await client.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=caption,
                reply_markup=kb
            )
    except Exception as e:
        print("ANIME ERROR:", e)
        await msg.edit_text(f"❌ Error:\n`{str(e)[:800]}`")


async def render_anime(client, query, data, token):
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
        photo = generate_anime_poster(base, data["info"], COLOURS[color])

    caption = build_anime_caption(data["info"], data["settings"])
    kb = build_anime_keyboard(token, page, len(posters), color, clean_mode)

    await query.message.edit_media(
        media=InputMediaPhoto(photo, caption=caption),
        reply_markup=kb
    )


@Client.on_callback_query(cb_starts("anicol|"), group=-910)
async def ani_color(client: Client, query: CallbackQuery):
    try:
        _, token, color = query.data.split("|")
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            return await query.answer("Expired / not yours", show_alert=True)
        if color not in COLOURS:
            return await query.answer("Invalid")
        data["color"] = color
        data["clean_mode"] = False
        await render_anime(client, query, data, token)
        await query.answer(f"Colour {color}")
    except Exception as e:
        print("ANI COLOR ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("anipage|"), group=-910)
async def ani_page(client: Client, query: CallbackQuery):
    try:
        _, token, page_s = query.data.split("|")
        page = int(page_s)
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            return await query.answer("Expired / not yours", show_alert=True)
        if page < 0 or page >= len(data["posters"]):
            return await query.answer("No more")
        data["page"] = page
        await render_anime(client, query, data, token)
        await query.answer(f"Page {page+1}")
    except Exception as e:
        print("ANI PAGE ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("aniclean|"), group=-910)
async def ani_clean(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            return await query.answer("Expired / not yours", show_alert=True)
        data["clean_mode"] = not data.get("clean_mode", False)
        await render_anime(client, query, data, token)
        await query.answer("Clean" if data["clean_mode"] else "Design")
    except Exception as e:
        print("ANI CLEAN ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("aniuse|"), group=-910)
async def ani_use(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            return await query.answer("Expired / not yours", show_alert=True)
        kb = build_anime_url_buttons(data["settings"])
        await query.message.edit_reply_markup(reply_markup=kb)
        await query.answer("✅ Buttons applied")
    except Exception as e:
        print("ANI USE ERR:", e)
        await query.answer("Error", show_alert=True)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("aniclear|"), group=-910)
async def ani_clear(client: Client, query: CallbackQuery):
    try:
        parts = query.data.split("|")
        token = parts[1] if len(parts) > 1 else None
        if token and token != "final":
            data = ANIME_CACHE.get(token)
            if data and query.from_user.id != data["user_id"]:
                return await query.answer("Not yours", show_alert=True)
            ANIME_CACHE.pop(token, None)
        try:
            await query.message.edit_caption("❌ Cleared.")
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.answer("Cleared")
    finally:
        raise StopPropagation


@Client.on_callback_query(filters.regex(r"^aninoop$"), group=-910)
async def ani_noop(_, query: CallbackQuery):
    await query.answer()
    raise StopPropagation


@Client.on_message(filters.command("animesettings") & filters.private)
async def anime_settings_cmd(client: Client, message: Message):
    s = load_anime_settings()
    text = (
        "⚙️ **ANIME SETTINGS**\n\n"
        f"🎧 **Audio:** `{s.get('audio')}`\n"
        f"📺 **Pixels:** `{s.get('pixels')}`\n"
        f"🔘 **Buttons:** `{len(s.get('buttons', []))} buttons`\n\n"
        "Manage options below:"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 CAPTION", callback_data="aset_caption"),
            InlineKeyboardButton("🎧 AUDIO", callback_data="aset_audio"),
        ],
        [
            InlineKeyboardButton("📺 PIXELS", callback_data="aset_pixels"),
            InlineKeyboardButton("🔘 BUTTONS", callback_data="aset_buttons"),
        ],
        [InlineKeyboardButton("🔄 RESET DEFAULT", callback_data="aset_reset")]
    ])
    await message.reply_text(text, reply_markup=kb)


@Client.on_callback_query(cb_starts("aset_"), group=-911)
async def anime_settings_cb(client: Client, query: CallbackQuery):
    action = query.data
    if action == "aset_caption":
        ANIME_STATE[query.from_user.id] = "wait_caption"
        await query.message.reply_text(
            "📝 Anime caption template bhej.\n\n"
            "Placeholders:\n"
            "`{title} {year} {status} {episodes} {rating} {pixels} {audio} {genres} {story}`\n\n"
            "/cancel"
        )
    elif action == "aset_audio":
        ANIME_STATE[query.from_user.id] = "wait_audio"
        await query.message.reply_text("🎧 Audio bhej\nExample: `Japanese | Hindi`\n/cancel")
    elif action == "aset_pixels":
        ANIME_STATE[query.from_user.id] = "wait_pixels"
        await query.message.reply_text("📺 Pixels bhej\nExample: `480p | 720p | 1080p`\n/cancel")
    elif action == "aset_buttons":
        ANIME_STATE[query.from_user.id] = "wait_buttons"
        await query.message.reply_text(
            "🔘 Format:\n`Button Text - https://link.com`\n"
            "Clear: `clear`\n/cancel"
        )
    elif action == "aset_reset":
        save_anime_settings(DEFAULT_ANIME_SETTINGS.copy())
        await query.answer("Reset done ✅", show_alert=True)
        await query.message.edit_text("✅ Anime settings reset.\nDobara /animesettings kar.")
    await query.answer()
    raise StopPropagation


@Client.on_message(filters.private & filters.text & ~filters.command(["anime", "animesettings", "post", "settings", "cancel", "img"]))
async def anime_settings_input(client: Client, message: Message):
    uid = message.from_user.id
    state = ANIME_STATE.get(uid)
    if not state:
        return

    text = message.text.strip()
    if text.lower() == "/cancel":
        ANIME_STATE.pop(uid, None)
        return await message.reply_text("❌ Cancelled.")

    s = load_anime_settings()

    if state == "wait_caption":
        s["caption_template"] = text
        save_anime_settings(s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text("✅ Anime caption save!")
    elif state == "wait_audio":
        s["audio"] = text
        save_anime_settings(s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ Audio: `{text}`")
    elif state == "wait_pixels":
        s["pixels"] = text
        save_anime_settings(s)
        ANIME_STATE.pop(uid, None)
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
        save_anime_settings(s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ {len(s['buttons'])} buttons save!")

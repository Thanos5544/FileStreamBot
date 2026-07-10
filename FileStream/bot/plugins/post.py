import os
import re
import json
import time
import uuid
import html
import aiohttp
import urllib.request
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
from pyrogram.enums import ParseMode
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

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
    "🟢": (16, 185, 129),
    "🔵": (37, 99, 235),
    "🟣": (147, 51, 234),
    "⚫": (24, 24, 24),
    "⚪": (245, 245, 245),
}

DEFAULT_SETTINGS = {
    "audio": "Hindi",
    "pixels": "480p | 720p | 1080p",
    "buttons": [],
    "font_style": "normal",
    "caption_template": "",
}

FONT_FILES = {
    "Montserrat-Bold.ttf": [
        "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
        "https://cdn.jsdelivr.net/gh/JulietaUla/Montserrat@master/fonts/ttf/Montserrat-Bold.ttf",
    ],
    "Montserrat-SemiBold.ttf": [
        "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-SemiBold.ttf",
        "https://cdn.jsdelivr.net/gh/JulietaUla/Montserrat@master/fonts/ttf/Montserrat-SemiBold.ttf",
    ],
    "Montserrat-Regular.ttf": [
        "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf",
        "https://cdn.jsdelivr.net/gh/JulietaUla/Montserrat@master/fonts/ttf/Montserrat-Regular.ttf",
    ],
}

SMALL_CAPS = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ғ", "g": "ɢ", "h": "ʜ",
    "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ",
    "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ", "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x",
    "y": "ʏ", "z": "ᴢ",
}

CAPTION_EXAMPLE = """{title}  (S{seasons}) ({year})
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


def to_small_caps(text: str) -> str:
    out = []
    for ch in text:
        low = ch.lower()
        if low in SMALL_CAPS and ch.isalpha():
            out.append(SMALL_CAPS[low])
        else:
            out.append(ch)
    return "".join(out)


def _read_all_settings():
    if not SETTINGS_FILE.exists():
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        # old global format ignore
        if "audio" in data and not any(str(k).isdigit() for k in data.keys()):
            return {}
        return data
    except Exception:
        return {}


def load_settings(user_id: int):
    all_data = _read_all_settings()
    user_data = all_data.get(str(user_id), {})
    if not isinstance(user_data, dict):
        user_data = {}
    out = DEFAULT_SETTINGS.copy()
    out.update(user_data)
    for k, v in DEFAULT_SETTINGS.items():
        if k not in out:
            out[k] = v
    return out


def save_settings(user_id: int, data: dict):
    all_data = _read_all_settings()
    all_data[str(user_id)] = data
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)


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
    for name, urls in FONT_FILES.items():
        path = FONT_DIR / name
        if path.exists() and path.stat().st_size > 10000:
            continue
        for url in urls:
            try:
                print(f"Downloading font: {name}")
                urllib.request.urlretrieve(url, path)
                if path.exists() and path.stat().st_size > 10000:
                    print(f"Font ready: {name}")
                    break
            except Exception as e:
                print(f"Font fail {name}: {e}")


def get_font(size, bold=False, semi=False):
    ensure_fonts()
    try:
        if bold:
            p = FONT_DIR / "Montserrat-Bold.ttf"
            if p.exists():
                return ImageFont.truetype(str(p), size)
        if semi:
            p = FONT_DIR / "Montserrat-SemiBold.ttf"
            if p.exists():
                return ImageFont.truetype(str(p), size)
        p = FONT_DIR / "Montserrat-Regular.ttf"
        if p.exists():
            return ImageFont.truetype(str(p), size)
    except Exception as e:
        print("get_font error:", e)
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
    tv = [x for x in filtered if x.get("media_type") == "tv"]
    movies = [x for x in filtered if x.get("media_type") == "movie"]
    pool = tv + movies
    if year:
        for x in pool:
            d = x.get("release_date") or x.get("first_air_date") or ""
            if d.startswith(year):
                return x
    return pool[0]


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


def generate_poster(base_img, info, accent):
    W, H = 1280, 720
    img = base_img.copy().resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(0.52)
    img = ImageEnhance.Contrast(img).enhance(1.28)
    img = ImageEnhance.Color(img).enhance(1.02)
    img = img.convert("RGBA")

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    ar, ag, ab = accent

    for x in range(0, 780):
        p = (1.0 - (x / 780.0)) ** 0.60
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, int(250 * p)))
        od.line([(x, 0), (x, H)], fill=(ar, ag, ab, int(28 * p)))

    for y in range(0, 90):
        a = int(45 * (1 - y / 90))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    for y in range(H - 140, H):
        a = int(70 * ((y - (H - 140)) / 140))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, a))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 10, H], fill=accent + (255,))

    f_title = get_font(74, bold=True)
    f_meta = get_font(21, semi=True)
    f_story = get_font(19)
    f_btn = get_font(21, bold=True)

    title = info.get("title", "Unknown").upper()
    year = info.get("year", "")
    rating = info.get("rating", "N/A")
    genres = info.get("genres", "")
    status = info.get("status", "")
    story = info.get("story", "")
    media_type = info.get("media_type", "movie")

    left = 72
    y = 175

    title_lines = wrap_text(title, f_title, 650, draw)[:2]
    for i, line in enumerate(title_lines):
        ty = y + i * 80
        draw.text((left + 2, ty + 2), line, font=f_title, fill=(0, 0, 0, 90))
        draw.text((left, ty), line, font=f_title, fill=(255, 255, 255, 250))
    y += len(title_lines) * 80 + 14

    draw.rectangle([left, y, left + 140, y + 6], fill=accent + (255,))
    y += 32

    meta_parts = []
    if year:
        meta_parts.append(str(year))
    if genres:
        g = genres.upper()
        parts = [p.strip() for p in g.split(",")]
        if len(parts) >= 2:
            g = f"{parts[0]} & {parts[1]}"
        meta_parts.append(g)
    if media_type == "tv" and status and status not in ["—", ""]:
        st = status.upper()
        if "RETURNING" in st:
            st = "RETURNING"
        meta_parts.append(st)
    meta = "  •  ".join(meta_parts)
    draw.text((left, y), meta[:76], font=f_meta, fill=(195, 195, 195, 230))
    y += 40

    if story:
        story_lines = wrap_text(story, f_story, 500, draw)[:4]
        for i, line in enumerate(story_lines):
            draw.text((left, y + i * 26), line, font=f_story, fill=(175, 175, 175, 160))
        y += len(story_lines) * 26 + 36
    else:
        y += 28

    btn_h = 50
    btn_y = min(y, H - 100)
    watch_w = 210
    draw.rounded_rectangle([left, btn_y, left + watch_w, btn_y + btn_h], radius=11, fill=accent + (255,))
    draw.text((left + 22, btn_y + 12), "▶  WATCH NOW", font=f_btn, fill=(255, 255, 255, 255))

    imdb_x = left + watch_w + 12
    imdb_w = 155
    draw.rounded_rectangle([imdb_x, btn_y, imdb_x + imdb_w, btn_y + btn_h], radius=11, fill=(0, 0, 0, 235))
    draw.rounded_rectangle([imdb_x, btn_y, imdb_x + imdb_w, btn_y + btn_h], radius=11, outline=(255, 255, 255, 65), width=2)
    draw.text((imdb_x + 28, btn_y + 12), f"{rating} IMDb", font=f_btn, fill=(255, 255, 255, 255))

    final = img.convert("RGB")
    bio = BytesIO()
    final.save(bio, format="JPEG", quality=95)
    bio.seek(0)
    bio.name = "poster.jpg"
    return bio


def make_clean_image(base_img):
    W, H = 1280, 720
    img = base_img.copy().resize((W, H), Image.LANCZOS)
    bio = BytesIO()
    img.save(bio, format="JPEG", quality=95)
    bio.seek(0)
    bio.name = "clean.jpg"
    return bio


def fresh_photo(bio: BytesIO) -> BytesIO:
    bio.seek(0)
    out = BytesIO(bio.read())
    out.name = "poster.jpg"
    out.seek(0)
    return out


def build_default_caption(info, settings):
    title = str(info.get("title", "Unknown"))
    year = str(info.get("year", "N/A"))
    seasons = info.get("seasons")
    status = str(info.get("status", "—"))
    episodes = str(info.get("episodes", "—"))
    rating = str(info.get("rating", "N/A"))
    pixels = str(settings.get("pixels", "480p | 720p | 1080p"))
    audio = str(settings.get("audio", "Hindi"))
    genres = str(info.get("genres", "—"))
    story = str(info.get("story", "No overview available."))
    media_type = info.get("media_type", "movie")

    if media_type == "tv" and seasons:
        head_title = f"{title}  (S{seasons}) ({year})"
    else:
        head_title = f"{title} ({year})"

    if media_type == "tv":
        head = (
            f"{head_title}\n"
            f"╭───────────────────\n"
            f" ➥ Status: {status}\n"
            f" ➥ Episodes: {episodes}\n"
            f" ➥ Ratings: {rating} IMDb\n"
            f" ➥ Pixels: {pixels}\n"
            f" ➥ Audio: {audio}\n"
            f"├───────────────────\n"
            f" ➥ Genres: {genres}\n"
            f"╰───────────────────"
        )
    else:
        head = (
            f"{head_title}\n"
            f"╭───────────────────\n"
            f" ➥ Ratings: {rating} IMDb\n"
            f" ➥ Pixels: {pixels}\n"
            f" ➥ Audio: {audio}\n"
            f"├───────────────────\n"
            f" ➥ Genres: {genres}\n"
            f"╰───────────────────"
        )
    return head, story


def build_caption(info, settings):
    font_style = settings.get("font_style", "normal")
    custom = (settings.get("caption_template") or "").strip()

    if custom and "{title}" in custom:
        raw = {
            "title": str(info.get("title", "Unknown")),
            "year": str(info.get("year", "N/A")),
            "status": str(info.get("status", "—")),
            "episodes": str(info.get("episodes", "—")),
            "seasons": str(info.get("seasons") or ""),
            "rating": str(info.get("rating", "N/A")),
            "pixels": str(settings.get("pixels", "480p | 720p | 1080p")),
            "audio": str(settings.get("audio", "Hindi")),
            "genres": str(info.get("genres", "—")),
            "story": str(info.get("story", "No overview available.")),
        }
        try:
            if "{story}" in custom:
                head = custom.split("{story}")[0].rstrip().rstrip("≡").rstrip()
                head_fmt = head.format(**{**raw, "story": ""})
                story = raw["story"]
            else:
                head_fmt = custom.format(**raw)
                story = raw["story"]
        except Exception:
            head_fmt, story = build_default_caption(info, settings)
    else:
        head_fmt, story = build_default_caption(info, settings)

    if font_style == "smallcaps":
        head_fmt = to_small_caps(head_fmt)
        story_line = to_small_caps(f"≡ {story}")
    else:
        story_line = f"≡ {story}"

    return f"{html.escape(head_fmt)}\n<blockquote>{html.escape(story_line)}</blockquote>"


def build_post_keyboard(token, page, total, current_color="🟣", clean_mode=False):
    colours = list(COLOURS.keys())
    color_btns = [
        InlineKeyboardButton(
            f"•{c}•" if c == current_color else c,
            callback_data=f"postcol|{token}|{c}"
        )
        for c in colours
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ PREV", callback_data=f"postpage|{token}|{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="postnoop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("NEXT ➡️", callback_data=f"postpage|{token}|{page+1}"))

    return InlineKeyboardMarkup([
        color_btns[:4],
        color_btns[4:],
        nav,
        [
            InlineKeyboardButton("🖼 CLEAN" if not clean_mode else "🎨 DESIGN", callback_data=f"postclean|{token}"),
            InlineKeyboardButton("✅ USE THIS", callback_data=f"postuse|{token}"),
        ],
        [InlineKeyboardButton("🗑 CLEAR", callback_data=f"postclear|{token}")],
    ])


def build_url_buttons(settings):
    rows = []
    for b in settings.get("buttons", []):
        if isinstance(b, dict) and b.get("text") and b.get("url"):
            rows.append([InlineKeyboardButton(b["text"], url=b["url"])])
    if not rows:
        rows = [[InlineKeyboardButton("No buttons in /settings", callback_data="postnoop")]]
    rows.append([InlineKeyboardButton("🗑 CLEAR", callback_data="postclear|final")])
    return InlineKeyboardMarkup(rows)

@Client.on_message(filters.command("post") & (filters.private | filters.group))
async def post_cmd(client: Client, message: Message):
    cleanup_cache()
    ensure_fonts()

    if not message.from_user:
        return await message.reply_text("❌ User nahi mila.")

    user_id = message.from_user.id

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n`/post movie or series name`\n\n"
            "Example:\n`/post the witcher`"
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

            for p in images_data.get("backdrops", [])[:20]:
                w = p.get("width") or 0
                h = p.get("height") or 0
                if w and h and w < h:
                    continue
                url = tmdb_img_url(p.get("file_path"))
                if url and url not in posters:
                    posters.append(url)

            if not posters and details.get("poster_path"):
                posters.append(tmdb_img_url(details["poster_path"]))
            if not posters:
                return await msg.edit_text("❌ Images nahi mile.")

            genres = ", ".join([g["name"] for g in details.get("genres", [])][:3]) or "—"
            rating = details.get("vote_average")
            rating = f"{rating:.1f}" if rating else "N/A"

            if media_type == "tv":
                status_raw = details.get("status") or "—"
                status = "Returning" if "Returning" in status_raw else status_raw
                eps = details.get("number_of_episodes")
                episodes = f"{eps}+" if eps else "—"
                seasons = details.get("number_of_seasons")
            else:
                status = "—"
                episodes = "—"
                seasons = None

            story = (details.get("overview") or "No overview available.").strip()
            if len(story) > 300:
                story = story[:297] + "..."

            info = {
                "title": get_title(details),
                "year": get_year(details),
                "rating": rating,
                "genres": genres,
                "status": status,
                "episodes": episodes,
                "seasons": seasons,
                "story": story,
                "media_type": media_type,
            }

            base = await download_image(session, posters[0])
            if not base:
                return await msg.edit_text("❌ Poster download fail.")

            settings = load_settings(user_id)
            photo = generate_poster(base, info, COLOURS["🟣"])
            caption = build_caption(info, settings)

            token = uuid.uuid4().hex[:12]
            POST_CACHE[token] = {
                "user_id": user_id,
                "info": info,
                "posters": posters,
                "page": 0,
                "color": "🟣",
                "clean_mode": False,
                "base_images": {0: base},
                "time": time.time(),
            }

            kb = build_post_keyboard(token, 0, len(posters), "🟣", False)

            try:
                await msg.delete()
            except Exception:
                pass

            await client.send_photo(
                chat_id=message.chat.id,
                photo=fresh_photo(photo),
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
    except Exception as e:
        print("POST ERROR:", e)
        try:
            await msg.edit_text(f"❌ Error:\n`{str(e)[:800]}`")
        except Exception:
            pass


async def render_and_edit(client, query, data, token):
    try:
        page = data["page"]
        color = data["color"]
        posters = data["posters"]
        clean_mode = data.get("clean_mode", False)
        user_id = data["user_id"]

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

        settings = load_settings(user_id)
        photo = fresh_photo(photo)
        caption = build_caption(data["info"], settings)
        kb = build_post_keyboard(token, page, len(posters), color, clean_mode)

        await query.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=kb
        )
    except Exception as e:
        print("RENDER ERR:", e)
        try:
            await query.answer("Update failed, try again", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(cb_starts("postcol|"), group=-999)
async def post_color(client: Client, query: CallbackQuery):
    try:
        _, token, color = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        if color not in COLOURS:
            await query.answer("Invalid")
            raise StopPropagation
        data["color"] = color
        data["clean_mode"] = False
        await query.answer(f"Colour {color}")
        await render_and_edit(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("COLOR ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("postpage|"), group=-999)
async def post_page(client: Client, query: CallbackQuery):
    try:
        _, token, page_s = query.data.split("|")
        page = int(page_s)
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        if page < 0 or page >= len(data["posters"]):
            await query.answer("No more")
            raise StopPropagation
        data["page"] = page
        await query.answer(f"Page {page + 1}")
        await render_and_edit(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("PAGE ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("postclean|"), group=-999)
async def post_clean(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        data["clean_mode"] = not data.get("clean_mode", False)
        await query.answer("Clean" if data["clean_mode"] else "Design")
        await render_and_edit(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("CLEAN ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("postuse|"), group=-999)
async def post_use(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        settings = load_settings(data["user_id"])
        kb = build_url_buttons(settings)
        await query.message.edit_reply_markup(reply_markup=kb)
        await query.answer("✅ Buttons applied")
    except StopPropagation:
        raise
    except Exception as e:
        print("USE ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("postclear|"), group=-999)
async def post_clear(client: Client, query: CallbackQuery):
    try:
        parts = query.data.split("|")
        token = parts[1] if len(parts) > 1 else None
        if token and token != "final":
            data = POST_CACHE.get(token)
            if data and query.from_user.id != data["user_id"]:
                await query.answer("Not yours", show_alert=True)
                raise StopPropagation
            POST_CACHE.pop(token, None)
        try:
            await query.message.edit_caption("❌ Cleared.")
        except Exception:
            pass
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.answer("Cleared")
    except StopPropagation:
        raise
    except Exception as e:
        print("CLEAR ERR:", e)
    raise StopPropagation


@Client.on_callback_query(filters.regex(r"^postnoop$"), group=-999)
async def post_noop(_, query: CallbackQuery):
    await query.answer()
    raise StopPropagation


@Client.on_message(filters.command("settings") & (filters.private | filters.group))
async def settings_cmd(client: Client, message: Message):
    if not message.from_user:
        return
    uid = message.from_user.id
    s = load_settings(uid)
    custom = (s.get("caption_template") or "").strip()
    cap_status = "Custom" if custom else "Default"
    text = (
        "⚙️ **POST SETTINGS** (sirf teri)\n\n"
        f"🎧 **Audio:** `{s.get('audio')}`\n"
        f"📺 **Pixels:** `{s.get('pixels')}`\n"
        f"🔤 **Font:** `{s.get('font_style', 'normal')}`\n"
        f"📝 **Caption:** `{cap_status}`\n"
        f"🔘 **Buttons:** `{len(s.get('buttons', []))} buttons`\n\n"
        "_Har user ki settings alag save hoti hain._"
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
        [InlineKeyboardButton("🔤 FONT STYLE", callback_data="set_font")],
        [InlineKeyboardButton("🔄 RESET DEFAULT", callback_data="set_reset")],
    ])
    await message.reply_text(text, reply_markup=kb)


@Client.on_callback_query(cb_starts("set_"), group=-998)
async def settings_cb(client: Client, query: CallbackQuery):
    try:
        action = query.data
        uid = query.from_user.id

        if action == "set_caption":
            USER_STATE[uid] = "wait_caption"
            await query.answer()
            await query.message.reply_text(
                "📝 **Apna caption template bhej** (sirf teri settings)\n\n"
                "**Placeholders:**\n"
                "`{title} {year} {status} {episodes} {seasons} {rating} {pixels} {audio} {genres} {story}`\n\n"
                "**Example (copy karke edit kar):**\n"
                f"```\n{CAPTION_EXAMPLE}\n```\n\n"
                "• Story auto Quote me aati hai\n"
                "• Default wapas: `default` likh ke bhej\n"
                "• Cancel: /cancel"
            )

        elif action == "set_audio":
            USER_STATE[uid] = "wait_audio"
            await query.answer()
            await query.message.reply_text("🎧 Audio bhej\nExample: Hindi / English\n/cancel")

        elif action == "set_pixels":
            USER_STATE[uid] = "wait_pixels"
            await query.answer()
            await query.message.reply_text("📺 Pixels bhej\nExample: 480p | 720p | 1080p\n/cancel")

        elif action == "set_buttons":
            USER_STATE[uid] = "wait_buttons"
            await query.answer()
            await query.message.reply_text(
                "🔘 Format:\n`Button Text - https://link.com`\nClear: `clear`\n/cancel"
            )

        elif action == "set_font":
            s = load_settings(uid)
            cur = s.get("font_style", "normal")
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ NORMAL" if cur == "normal" else "NORMAL", callback_data="set_font_normal"),
                InlineKeyboardButton("✅ SMALL CAPS" if cur == "smallcaps" else "SMALL CAPS", callback_data="set_font_smallcaps"),
            ]])
            await query.answer()
            await query.message.edit_text(
                f"🔤 **Caption Font Style**\n\nCurrent: `{cur}`",
                reply_markup=kb
            )

        elif action == "set_font_normal":
            s = load_settings(uid)
            s["font_style"] = "normal"
            save_settings(uid, s)
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ NORMAL", callback_data="set_font_normal"),
                InlineKeyboardButton("SMALL CAPS", callback_data="set_font_smallcaps"),
            ]])
            await query.answer("Font: NORMAL ✅", show_alert=True)
            await query.message.edit_text(
                "🔤 **Caption Font Style**\n\nCurrent: `normal`",
                reply_markup=kb
            )

        elif action == "set_font_smallcaps":
            s = load_settings(uid)
            s["font_style"] = "smallcaps"
            save_settings(uid, s)
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("NORMAL", callback_data="set_font_normal"),
                InlineKeyboardButton("✅ SMALL CAPS", callback_data="set_font_smallcaps"),
            ]])
            await query.answer("Font: SMALL CAPS ✅", show_alert=True)
            await query.message.edit_text(
                "🔤 **Caption Font Style**\n\nCurrent: `smallcaps`",
                reply_markup=kb
            )

        elif action == "set_reset":
            save_settings(uid, DEFAULT_SETTINGS.copy())
            await query.answer("Teri settings reset ✅", show_alert=True)

        else:
            await query.answer()

    except Exception as e:
        print("SETTINGS CB ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_message((filters.private | filters.group) & filters.text, group=50)
async def settings_input(client: Client, message: Message):
    if not message.from_user:
        return
    uid = message.from_user.id
    state = USER_STATE.get(uid)
    if not state:
        return
    if message.text and message.text.startswith("/"):
        return

    text = message.text.strip()
    s = load_settings(uid)

    if state == "wait_caption":
        s["caption_template"] = "" if text.lower() == "default" else text
        save_settings(uid, s)
        USER_STATE.pop(uid, None)
        await message.reply_text("✅ Teri caption save!")
    elif state == "wait_audio":
        s["audio"] = text
        save_settings(uid, s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ Tera audio: `{text}`")
    elif state == "wait_pixels":
        s["pixels"] = text
        save_settings(uid, s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ Tere pixels: `{text}`")
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
        save_settings(uid, s)
        USER_STATE.pop(uid, None)
        await message.reply_text(f"✅ Tere {len(s['buttons'])} buttons save!")


@Client.on_message(filters.command("cancel") & (filters.private | filters.group))
async def cancel_state(_, message: Message):
    if not message.from_user:
        return
    USER_STATE.pop(message.from_user.id, None)
    await message.reply_text("✅ Cleared.")

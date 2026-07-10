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
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

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

# 13 neon anime colours
COLOURS = {
    "🔴": (255, 59, 78),
    "🟠": (255, 140, 50),
    "🟡": (255, 214, 10),
    "🟢": (50, 215, 120),
    "🔵": (64, 156, 255),
    "🟣": (191, 90, 242),
    "🩷": (255, 105, 180),
    "🩵": (100, 210, 255),
    "⚪": (245, 245, 250),
    "⚫": (40, 40, 48),
    "🟤": (180, 120, 80),
    "💚": (80, 220, 160),
    "💙": (90, 130, 255),
}

DEFAULT_SETTINGS = {
    "audio": "Japanese | Hindi",
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

CAPTION_EXAMPLE = """✦ {title}
──────────────
◎ Type: Anime
◎ Season: S{seasons}
◎ Status: {status}
◎ Episodes: {episodes}
◎ Rating: ★ {rating}
◎ Quality: {pixels}
◎ Audio: {audio}
◎ Genres: {genres}
──────────────
✧ {story}"""


def to_small_caps(text: str) -> str:
    out = []
    for ch in text:
        low = ch.lower()
        if low in SMALL_CAPS and ch.isalpha():
            out.append(SMALL_CAPS[low])
        else:
            out.append(ch)
    return "".join(out)


def _read_all():
    if not ANIME_SETTINGS_FILE.exists():
        return {}
    try:
        with open(ANIME_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        if "audio" in data and not any(str(k).isdigit() for k in data.keys()):
            return {}
        return data
    except Exception:
        return {}


def load_settings(user_id: int):
    all_data = _read_all()
    user = all_data.get(str(user_id), {})
    if not isinstance(user, dict):
        user = {}
    out = DEFAULT_SETTINGS.copy()
    out.update(user)
    for k, v in DEFAULT_SETTINGS.items():
        if k not in out:
            out[k] = v
    return out


def save_settings(user_id: int, data: dict):
    all_data = _read_all()
    all_data[str(user_id)] = data
    with open(ANIME_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)


def cleanup_cache():
    now = time.time()
    for token in list(ANIME_CACHE.keys()):
        if now - ANIME_CACHE[token].get("time", now) > CACHE_TIME:
            ANIME_CACHE.pop(token, None)


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
                print(f"[ANIME] Downloading font: {name}")
                urllib.request.urlretrieve(url, path)
                if path.exists() and path.stat().st_size > 10000:
                    print(f"[ANIME] Font ready: {name}")
                    break
            except Exception as e:
                print(f"[ANIME] Font fail {name}: {e}")


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
        params={"api_key": TMDB_API, "include_image_language": "en,ja,null"}
    ) as resp:
        return await resp.json()


def select_anime(results, year=None):
    filtered = [x for x in results if x.get("media_type") in ("movie", "tv")]
    if not filtered:
        return None
    # prefer TV for anime series
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


def generate_anime_poster(base_img, info, accent):
    """
    Soft Neon Anime template
    - soft dark (art preserve)
    - neon left bar
    - soft wash + glow title
    - ANIME chip
    - totally different from post.py
    """
    W, H = 1280, 720

    img = base_img.copy().resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(0.72)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.18)
    img = img.convert("RGBA")

    # soft blur layer for glow base
    glow_layer = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    img = Image.blend(img, glow_layer, 0.18)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    ar, ag, ab = accent

    # soft left panel (not heavy black)
    for x in range(0, 700):
        p = (1.0 - (x / 700.0)) ** 0.75
        od.line([(x, 0), (x, H)], fill=(8, 10, 22, int(185 * p)))
        od.line([(x, 0), (x, H)], fill=(ar, ag, ab, int(45 * p)))

    # neon edge bar
    od.rectangle([0, 0, 8, H], fill=accent + (255,))
    # soft neon glow next to bar
    for i, a in enumerate([70, 40, 20]):
        od.line([(9 + i, 0), (9 + i, H)], fill=(ar, ag, ab, a))

    # top/bottom soft vignette
    for y in range(0, 70):
        od.line([(0, y), (W, y)], fill=(0, 0, 0, int(35 * (1 - y / 70))))
    for y in range(H - 110, H):
        od.line([(0, y), (W, y)], fill=(0, 0, 0, int(50 * ((y - (H - 110)) / 110))))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    f_title = get_font(68, bold=True)
    f_meta = get_font(20, semi=True)
    f_story = get_font(18)
    f_btn = get_font(20, bold=True)
    f_chip = get_font(15, bold=True)

    title = info.get("title", "Unknown").upper()
    year = info.get("year", "")
    rating = info.get("rating", "N/A")
    genres = info.get("genres", "")
    status = info.get("status", "")
    story = info.get("story", "")
    seasons = info.get("seasons")

    left = 68
    y = 95

    # ANIME chip
    chip_w, chip_h = 110, 30
    draw.rounded_rectangle([left, y, left + chip_w, y + chip_h], radius=15, fill=accent + (240,))
    draw.text((left + 18, y + 6), "✦ ANIME", font=f_chip, fill=(255, 255, 255, 255))
    y += 50

    # TITLE soft glow
    title_lines = wrap_text(title, f_title, 620, draw)[:2]
    for i, line in enumerate(title_lines):
        ty = y + i * 72
        # glow
        for ox, oy, aa in [(0, 0, 50), (2, 2, 80), (-1, 1, 40)]:
            draw.text((left + ox, ty + oy), line, font=f_title, fill=(ar, ag, ab, aa))
        draw.text((left + 2, ty + 2), line, font=f_title, fill=(0, 0, 0, 100))
        draw.text((left, ty), line, font=f_title, fill=(255, 255, 255, 250))
    y += len(title_lines) * 72 + 10

    # neon underline
    draw.rectangle([left, y, left + 160, y + 5], fill=accent + (255,))
    # soft underline glow
    draw.rectangle([left, y + 5, left + 160, y + 8], fill=(ar, ag, ab, 60))
    y += 28

    # meta
    meta_parts = []
    if year:
        meta_parts.append(str(year))
    if seasons:
        meta_parts.append(f"S{seasons}")
    if genres:
        g = genres.upper()
        parts = [p.strip() for p in g.split(",")]
        if len(parts) >= 2:
            g = f"{parts[0]} · {parts[1]}"
        meta_parts.append(g)
    if status and status not in ["—", ""]:
        st = status.upper()
        if "RETURNING" in st:
            st = "RETURNING"
        meta_parts.append(st)
    meta = "  ·  ".join(meta_parts)
    draw.text((left, y), meta[:78], font=f_meta, fill=(210, 215, 230, 230))
    y += 38

    # story soft
    if story:
        story_lines = wrap_text(story, f_story, 500, draw)[:4]
        for i, line in enumerate(story_lines):
            draw.text((left, y + i * 25), line, font=f_story, fill=(190, 195, 210, 170))
        y += len(story_lines) * 25 + 34
    else:
        y += 26

    # buttons - soft neon style
    btn_h = 48
    btn_y = min(y, H - 100)

    watch_w = 200
    draw.rounded_rectangle([left, btn_y, left + watch_w, btn_y + btn_h], radius=24, fill=accent + (255,))
    draw.text((left + 28, btn_y + 12), "▶  WATCH", font=f_btn, fill=(255, 255, 255, 255))

    score_x = left + watch_w + 12
    score_w = 150
    draw.rounded_rectangle([score_x, btn_y, score_x + score_w, btn_y + btn_h], radius=24, fill=(12, 14, 24, 220))
    draw.rounded_rectangle(
        [score_x, btn_y, score_x + score_w, btn_y + btn_h],
        radius=24,
        outline=(ar, ag, ab, 140),
        width=2
    )
    draw.text((score_x + 28, btn_y + 12), f"★ {rating}", font=f_btn, fill=(255, 255, 255, 255))

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


def fresh_photo(bio: BytesIO) -> BytesIO:
    bio.seek(0)
    out = BytesIO(bio.read())
    out.name = "anime.jpg"
    out.seek(0)
    return out


def build_default_caption(info, settings):
    title = str(info.get("title", "Unknown"))
    seasons = info.get("seasons")
    status = str(info.get("status", "—"))
    episodes = str(info.get("episodes", "—"))
    rating = str(info.get("rating", "N/A"))
    pixels = str(settings.get("pixels", "480p | 720p | 1080p"))
    audio = str(settings.get("audio", "Japanese | Hindi"))
    genres = str(info.get("genres", "—"))
    story = str(info.get("story", "No overview available."))
    media_type = info.get("media_type", "tv")

    season_txt = f"S{seasons}" if (media_type == "tv" and seasons) else "—"

    if media_type == "tv":
        head = (
            f"✦ {title}\n"
            f"──────────────\n"
            f"◎ Type: Anime\n"
            f"◎ Season: {season_txt}\n"
            f"◎ Status: {status}\n"
            f"◎ Episodes: {episodes}\n"
            f"◎ Rating: ★ {rating}\n"
            f"◎ Quality: {pixels}\n"
            f"◎ Audio: {audio}\n"
            f"◎ Genres: {genres}\n"
            f"──────────────"
        )
    else:
        head = (
            f"✦ {title}\n"
            f"──────────────\n"
            f"◎ Type: Anime Movie\n"
            f"◎ Rating: ★ {rating}\n"
            f"◎ Quality: {pixels}\n"
            f"◎ Audio: {audio}\n"
            f"◎ Genres: {genres}\n"
            f"──────────────"
        )
    return f"{head}\n✧ {story}"


def build_caption(info, settings):
    font_style = settings.get("font_style", "normal")
    custom = (settings.get("caption_template") or "").strip()

    raw = {
        "title": str(info.get("title", "Unknown")),
        "year": str(info.get("year", "N/A")),
        "status": str(info.get("status", "—")),
        "episodes": str(info.get("episodes", "—")),
        "seasons": str(info.get("seasons") or ""),
        "rating": str(info.get("rating", "N/A")),
        "pixels": str(settings.get("pixels", "480p | 720p | 1080p")),
        "audio": str(settings.get("audio", "Japanese | Hindi")),
        "genres": str(info.get("genres", "—")),
        "story": str(info.get("story", "No overview available.")),
    }

    if custom:
        try:
            if info.get("media_type") != "tv":
                raw["seasons"] = ""
            caption = custom.format(**raw)
            caption = caption.replace("  (S) ", " ").replace("(S) ", "")
            caption = re.sub(r"\n{3,}", "\n\n", caption).strip()
        except Exception as e:
            print("ANIME CAPTION ERR:", e)
            caption = build_default_caption(info, settings)
    else:
        caption = build_default_caption(info, settings)

    if font_style == "smallcaps":
        caption = to_small_caps(caption)

    # story quote if ✧ or ≡ present
    for mark in ("✧", "≡"):
        if mark in caption:
            head, story = caption.rsplit(mark, 1)
            head = head.rstrip()
            story = (mark + story).strip()
            return f"{html.escape(head)}\n<blockquote>{html.escape(story)}</blockquote>"

    return html.escape(caption)


def build_anime_keyboard(token, page, total, current_color="🩷", clean_mode=False):
    colours = list(COLOURS.keys())
    # 13 colours -> 5 + 4 + 4
    color_btns = [
        InlineKeyboardButton(
            f"•{c}•" if c == current_color else c,
            callback_data=f"anicol|{token}|{c}"
        )
        for c in colours
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⟵ Prev", callback_data=f"anipage|{token}|{page-1}"))
    nav.append(InlineKeyboardButton(f"· {page+1}/{total} ·", callback_data="aninoop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("Next ⟶", callback_data=f"anipage|{token}|{page+1}"))

    return InlineKeyboardMarkup([
        color_btns[:5],
        color_btns[5:9],
        color_btns[9:],
        nav,
        [
            InlineKeyboardButton("✧ Clean" if not clean_mode else "✦ Design", callback_data=f"aniclean|{token}"),
            InlineKeyboardButton("✓ Use This", callback_data=f"aniuse|{token}"),
        ],
        [InlineKeyboardButton("✕ Clear", callback_data=f"aniclear|{token}")],
    ])


def build_url_buttons(settings):
    rows = []
    for b in settings.get("buttons", []):
        if isinstance(b, dict) and b.get("text") and b.get("url"):
            rows.append([InlineKeyboardButton(b["text"], url=b["url"])])
    if not rows:
        rows = [[InlineKeyboardButton("No buttons in /animesettings", callback_data="aninoop")]]
    rows.append([InlineKeyboardButton("✕ Clear", callback_data="aniclear|final")])
    return InlineKeyboardMarkup(rows)

@Client.on_message(filters.command("anime") & (filters.private | filters.group))
async def anime_cmd(client: Client, message: Message):
    cleanup_cache()
    ensure_fonts()

    if not message.from_user:
        return await message.reply_text("❌ User nahi mila.")

    user_id = message.from_user.id

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n`/anime anime name`\n\n"
            "Example:\n`/anime naruto`\n`/anime demon slayer`"
        )

    query = " ".join(message.command[1:]).strip()
    msg = await message.reply_text("✦ Searching anime & crafting poster...")

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
                return await msg.edit_text("❌ Anime nahi mila.")

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
            if len(story) > 280:
                story = story[:277] + "..."

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
            photo = generate_anime_poster(base, info, COLOURS["🩷"])
            caption = build_caption(info, settings)

            token = uuid.uuid4().hex[:12]
            ANIME_CACHE[token] = {
                "user_id": user_id,
                "info": info,
                "posters": posters,
                "page": 0,
                "color": "🩷",
                "clean_mode": False,
                "base_images": {0: base},
                "time": time.time(),
            }

            kb = build_anime_keyboard(token, 0, len(posters), "🩷", False)

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
        print("ANIME ERROR:", e)
        try:
            await msg.edit_text(f"❌ Error:\n`{str(e)[:800]}`")
        except Exception:
            pass


async def render_anime(client, query, data, token):
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
            photo = generate_anime_poster(base, data["info"], COLOURS[color])

        settings = load_settings(user_id)
        photo = fresh_photo(photo)
        caption = build_caption(data["info"], settings)
        kb = build_anime_keyboard(token, page, len(posters), color, clean_mode)

        await query.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=kb
        )
    except Exception as e:
        print("ANIME RENDER ERR:", e)
        try:
            await query.answer("Update failed", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(cb_starts("anicol|"), group=-989)
async def ani_color(client: Client, query: CallbackQuery):
    try:
        _, token, color = query.data.split("|")
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        if color not in COLOURS:
            await query.answer("Invalid")
            raise StopPropagation
        data["color"] = color
        data["clean_mode"] = False
        await query.answer(f"Colour {color}")
        await render_anime(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI COLOR ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("anipage|"), group=-989)
async def ani_page(client: Client, query: CallbackQuery):
    try:
        _, token, page_s = query.data.split("|")
        page = int(page_s)
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        if page < 0 or page >= len(data["posters"]):
            await query.answer("No more")
            raise StopPropagation
        data["page"] = page
        await query.answer(f"Page {page + 1}")
        await render_anime(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI PAGE ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("aniclean|"), group=-989)
async def ani_clean(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        data["clean_mode"] = not data.get("clean_mode", False)
        await query.answer("Clean" if data["clean_mode"] else "Design")
        await render_anime(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI CLEAN ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("aniuse|"), group=-989)
async def ani_use(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Expired / not yours", show_alert=True)
            raise StopPropagation
        settings = load_settings(data["user_id"])
        kb = build_url_buttons(settings)
        await query.message.edit_reply_markup(reply_markup=kb)
        await query.answer("✓ Applied")
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI USE ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_callback_query(cb_starts("aniclear|"), group=-989)
async def ani_clear(client: Client, query: CallbackQuery):
    try:
        parts = query.data.split("|")
        token = parts[1] if len(parts) > 1 else None
        if token and token != "final":
            data = ANIME_CACHE.get(token)
            if data and query.from_user.id != data["user_id"]:
                await query.answer("Not yours", show_alert=True)
                raise StopPropagation
            ANIME_CACHE.pop(token, None)
        try:
            await query.message.edit_caption("✕ Cleared.")
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
        print("ANI CLEAR ERR:", e)
    raise StopPropagation


@Client.on_callback_query(filters.regex(r"^aninoop$"), group=-989)
async def ani_noop(_, query: CallbackQuery):
    await query.answer()
    raise StopPropagation


@Client.on_message(filters.command("animesettings") & (filters.private | filters.group))
async def anime_settings_cmd(client: Client, message: Message):
    if not message.from_user:
        return
    uid = message.from_user.id
    s = load_settings(uid)
    custom = (s.get("caption_template") or "").strip()
    text = (
        "✦ **ANIME SETTINGS** (sirf teri)\n\n"
        f"🎧 **Audio:** `{s.get('audio')}`\n"
        f"📺 **Quality:** `{s.get('pixels')}`\n"
        f"🔤 **Font:** `{s.get('font_style', 'normal')}`\n"
        f"📝 **Caption:** `{'Custom' if custom else 'Default'}`\n"
        f"🔘 **Buttons:** `{len(s.get('buttons', []))} buttons`\n\n"
        "_PM + Group same settings_"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 CAPTION", callback_data="aset_caption"),
            InlineKeyboardButton("🎧 AUDIO", callback_data="aset_audio"),
        ],
        [
            InlineKeyboardButton("📺 QUALITY", callback_data="aset_pixels"),
            InlineKeyboardButton("🔘 BUTTONS", callback_data="aset_buttons"),
        ],
        [InlineKeyboardButton("🔤 FONT", callback_data="aset_font")],
        [InlineKeyboardButton("↺ RESET", callback_data="aset_reset")],
    ])
    await message.reply_text(text, reply_markup=kb)


@Client.on_callback_query(cb_starts("aset_"), group=-988)
async def anime_settings_cb(client: Client, query: CallbackQuery):
    try:
        action = query.data
        uid = query.from_user.id

        if action == "aset_caption":
            ANIME_STATE[uid] = "wait_caption"
            await query.answer()
            await query.message.reply_text(
                "📝 **Anime caption template** bhej\n\n"
                "**Placeholders:**\n"
                "`{title} {year} {status} {episodes} {seasons} {rating} {pixels} {audio} {genres} {story}`\n\n"
                "**Example:**\n"
                f"```\n{CAPTION_EXAMPLE}\n```\n\n"
                "• `{story}` se story control\n"
                "• Default: `default`\n"
                "• Cancel: /anicancel"
            )

        elif action == "aset_audio":
            ANIME_STATE[uid] = "wait_audio"
            await query.answer()
            await query.message.reply_text("🎧 Audio bhej\nExample: `Japanese | Hindi`\n/anicancel")

        elif action == "aset_pixels":
            ANIME_STATE[uid] = "wait_pixels"
            await query.answer()
            await query.message.reply_text("📺 Quality bhej\nExample: `480p | 720p | 1080p`\n/anicancel")

        elif action == "aset_buttons":
            ANIME_STATE[uid] = "wait_buttons"
            await query.answer()
            await query.message.reply_text(
                "🔘 Format:\n`Button Text - https://link.com`\nClear: `clear`\n/anicancel"
            )

        elif action == "aset_font":
            s = load_settings(uid)
            cur = s.get("font_style", "normal")
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ NORMAL" if cur == "normal" else "NORMAL", callback_data="aset_font_normal"),
                InlineKeyboardButton("✅ SMALL CAPS" if cur == "smallcaps" else "SMALL CAPS", callback_data="aset_font_smallcaps"),
            ]])
            await query.answer()
            await query.message.edit_text(
                f"🔤 **Font Style**\n\nCurrent: `{cur}`",
                reply_markup=kb
            )

        elif action == "aset_font_normal":
            s = load_settings(uid)
            s["font_style"] = "normal"
            save_settings(uid, s)
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ NORMAL", callback_data="aset_font_normal"),
                InlineKeyboardButton("SMALL CAPS", callback_data="aset_font_smallcaps"),
            ]])
            await query.answer("NORMAL ✅", show_alert=True)
            await query.message.edit_text("🔤 **Font Style**\n\nCurrent: `normal`", reply_markup=kb)

        elif action == "aset_font_smallcaps":
            s = load_settings(uid)
            s["font_style"] = "smallcaps"
            save_settings(uid, s)
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("NORMAL", callback_data="aset_font_normal"),
                InlineKeyboardButton("✅ SMALL CAPS", callback_data="aset_font_smallcaps"),
            ]])
            await query.answer("SMALL CAPS ✅", show_alert=True)
            await query.message.edit_text("🔤 **Font Style**\n\nCurrent: `smallcaps`", reply_markup=kb)

        elif action == "aset_reset":
            save_settings(uid, DEFAULT_SETTINGS.copy())
            await query.answer("Reset ✅", show_alert=True)

        else:
            await query.answer()

    except Exception as e:
        print("ASET ERR:", e)
        try:
            await query.answer("Error", show_alert=True)
        except Exception:
            pass
    raise StopPropagation


@Client.on_message((filters.private | filters.group) & filters.text, group=52)
async def anime_settings_input(client: Client, message: Message):
    if not message.from_user:
        return
    uid = message.from_user.id
    state = ANIME_STATE.get(uid)
    if not state:
        return
    if message.text and message.text.startswith("/"):
        return

    text = message.text.strip()
    s = load_settings(uid)

    if state == "wait_caption":
        s["caption_template"] = "" if text.lower() == "default" else text
        save_settings(uid, s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text("✅ Anime caption save!\nAb `/anime name` maaro.")
    elif state == "wait_audio":
        s["audio"] = text
        save_settings(uid, s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ Audio: `{text}`")
    elif state == "wait_pixels":
        s["pixels"] = text
        save_settings(uid, s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ Quality: `{text}`")
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
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ {len(s['buttons'])} buttons save!")


@Client.on_message(filters.command("anicancel") & (filters.private | filters.group))
async def anime_cancel(_, message: Message):
    if not message.from_user:
        return
    ANIME_STATE.pop(message.from_user.id, None)
    await message.reply_text("✅ Anime state cleared.")

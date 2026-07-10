import os
import re
import json
import time
import uuid
import html
import math
import aiohttp
import urllib.request
from io import BytesIO
from pathlib import Path

from pyrogram import Client, filters, StopPropagation
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, InputMediaPhoto
)
from pyrogram.enums import ParseMode
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

DEFAULT_SETTINGS = {
    "audio": "Japanese | Hindi",
    "pixels": "720p | 1080p",
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

CAPTION_EXAMPLE = """{title}

» Type: Anime
» Average Rating: {rating_pct}%
» Status: {status}
» Episodes: {episodes}
» Genres: {genres}

‣ SYNOPSIS
➟ {story}"""


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
    return filters.create(lambda _, __, q: bool(q.data and q.data.startswith(prefix)))


def ensure_fonts():
    for name, urls in FONT_FILES.items():
        path = FONT_DIR / name
        if path.exists() and path.stat().st_size > 10000:
            continue
        for url in urls:
            try:
                urllib.request.urlretrieve(url, path)
                if path.exists() and path.stat().st_size > 10000:
                    break
            except Exception as e:
                print("Font fail", name, e)


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
    except Exception:
        pass
    return ImageFont.load_default()


def tmdb_img_url(path):
    return (TMDB_IMG + path) if path else None


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
    pool = [x for x in filtered if x.get("media_type") == "tv"] + [
        x for x in filtered if x.get("media_type") == "movie"
    ]
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
                return Image.open(BytesIO(await resp.read())).convert("RGB")
    except Exception as e:
        print("dl err", e)
    return None


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ""
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


def cover_crop(img, tw, th):
    """center crop, no stretch"""
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def draw_star(draw, cx, cy, r, fill, outline=None):
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill, outline=outline)


def draw_rating_stars(draw, x, y, rating_10, size=10, gap=17):
    try:
        val = float(rating_10)
    except Exception:
        val = 0.0
    filled = int(round(val / 2.0))
    filled = max(0, min(5, filled))
    for i in range(5):
        cx = x + i * gap + size
        cy = y + size
        if i < filled:
            draw_star(draw, cx, cy, size, fill=(255, 185, 30), outline=(230, 150, 10))
        else:
            draw_star(draw, cx, cy, size, fill=(230, 230, 235), outline=(200, 200, 210))
    return 5 * gap


def draw_bookmark_icon(draw, box, color=(20, 20, 25)):
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    draw.ellipse([x1, y1, x2, y2], outline=color, width=3)
    bw, bh = 14, 20
    bx1 = cx - bw / 2
    by1 = cy - bh / 2 + 1
    bx2 = cx + bw / 2
    by2 = cy + bh / 2
    draw.polygon([
        (bx1, by1),
        (bx2, by1),
        (bx2, by2),
        (cx, by2 - 7),
        (bx1, by2),
    ], fill=color)


def generate_anime_poster(base_img, info):
    """
    Split card:
    LEFT art | RIGHT white panel
    NO branding, NO colour buttons
    """
    W, H = 1280, 720
    LEFT_W = 620
    RIGHT_W = W - LEFT_W

    canvas = Image.new("RGB", (W, H), (255, 255, 255))

    art = cover_crop(base_img.convert("RGB"), LEFT_W, H)
    art = ImageEnhance.Brightness(art).enhance(0.96)
    art = ImageEnhance.Contrast(art).enhance(1.06)
    canvas.paste(art, (0, 0))

    art_rgba = art.convert("RGBA")
    fade = Image.new("RGBA", (LEFT_W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    for y in range(H - 120, H):
        a = int(80 * ((y - (H - 120)) / 120))
        fd.line([(0, y), (LEFT_W, y)], fill=(0, 0, 0, a))
    canvas.paste(Image.alpha_composite(art_rgba, fade).convert("RGB"), (0, 0))

    draw = ImageDraw.Draw(canvas)

    f_title = get_font(56, bold=True)
    f_chip = get_font(15, semi=True)
    f_body = get_font(17)
    f_small = get_font(16, semi=True)
    f_btn = get_font(17, bold=True)

    title = str(info.get("title", "Unknown")).upper()
    rating = info.get("rating", "N/A")
    try:
        rating_f = float(rating)
    except Exception:
        rating_f = 0.0

    genres = [g.strip() for g in str(info.get("genres", "")).split(",") if g.strip()]
    clean_g = []
    for g in genres:
        g2 = (
            g.replace("Action & Adventure", "Action")
             .replace("Sci-Fi & Fantasy", "Fantasy")
             .replace("Science Fiction", "Sci-Fi")
        )
        clean_g.append(g2)
    genres = clean_g[:2]

    story = str(info.get("story", "No overview available."))

    rx = LEFT_W + 50
    max_text_w = RIGHT_W - 100

    y = 105
    t_lines = wrap_text(title, f_title, max_text_w, draw)[:2]
    for i, line in enumerate(t_lines):
        draw.text((rx, y + i * 60), line, font=f_title, fill=(15, 15, 20))
    y += len(t_lines) * 60 + 20

    px, py = rx, y
    for g in genres:
        gw = int(draw.textlength(g, font=f_chip)) + 24
        draw.rounded_rectangle([px, py, px + gw, py + 28], radius=14, outline=(215, 215, 220), width=2)
        draw.text((px + 12, py + 5), g, font=f_chip, fill=(55, 55, 65))
        px += gw + 10

    ax = px + 14
    draw.text((ax, py + 4), "Avg Ratings:", font=f_small, fill=(35, 35, 42))
    star_x = ax + int(draw.textlength("Avg Ratings: ", font=f_small)) + 2
    draw_rating_stars(draw, star_x, py + 3, rating_f, size=10, gap=17)
    y = py + 52

    draw.line([(rx, y), (W - 50, y)], fill=(232, 232, 236), width=2)
    y += 26

    syn_lines = wrap_text(story.upper(), f_body, max_text_w, draw)[:6]
    for i, line in enumerate(syn_lines):
        draw.text((rx, y + i * 27), line, font=f_body, fill=(115, 118, 128))
    y += max(len(syn_lines), 1) * 27 + 38

    btn_w, btn_h = 188, 48
    by = min(y, H - 105)
    draw.rounded_rectangle([rx, by, rx + btn_w, by + btn_h], radius=24, fill=(12, 12, 16))
    draw.text((rx + 30, by + 13), "WATCH ", font=f_btn, fill=(255, 255, 255))
    nw = int(draw.textlength("WATCH ", font=f_btn))
    draw.text((rx + 30 + nw, by + 13), "NOW", font=f_btn, fill=(255, 55, 70))

    bx1 = rx + btn_w + 16
    draw_bookmark_icon(draw, (bx1, by, bx1 + btn_h, by + btn_h), color=(20, 20, 25))

    bio = BytesIO()
    canvas.save(bio, format="JPEG", quality=95)
    bio.seek(0)
    bio.name = "anime.jpg"
    return bio


def make_clean_image(base_img):
    img = cover_crop(base_img.convert("RGB"), 1280, 720)
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


def rating_to_pct(rating):
    try:
        return str(int(round(float(rating) * 10)))
    except Exception:
        return "0"


def build_default_caption(info, settings):
    title = str(info.get("title", "Unknown"))
    status = str(info.get("status", "—"))
    episodes = str(info.get("episodes", "—"))
    genres = str(info.get("genres", "—"))
    story = str(info.get("story", "No overview available."))
    rating = str(info.get("rating", "N/A"))
    pct = rating_to_pct(rating)
    media_type = info.get("media_type", "tv")
    type_txt = "Anime" if media_type == "tv" else "Anime Movie"

    return (
        f"{title}\n\n"
        f"» Type: {type_txt}\n"
        f"» Average Rating: {pct}%\n"
        f"» Status: {status}\n"
        f"» Episodes: {episodes}\n"
        f"» Genres: {genres}\n\n"
        f"‣ SYNOPSIS\n"
        f"➟ {story}"
    )


def build_caption(info, settings):
    font_style = settings.get("font_style", "normal")
    custom = (settings.get("caption_template") or "").strip()

    rating = str(info.get("rating", "N/A"))
    raw = {
        "title": str(info.get("title", "Unknown")),
        "year": str(info.get("year", "N/A")),
        "status": str(info.get("status", "—")),
        "episodes": str(info.get("episodes", "—")),
        "seasons": str(info.get("seasons") or ""),
        "rating": rating,
        "rating_pct": rating_to_pct(rating),
        "pixels": str(settings.get("pixels", "720p | 1080p")),
        "audio": str(settings.get("audio", "Japanese | Hindi")),
        "genres": str(info.get("genres", "—")),
        "story": str(info.get("story", "No overview available.")),
    }

    if custom:
        try:
            caption = custom.format(**raw)
            caption = re.sub(r"\n{3,}", "\n\n", caption).strip()
        except Exception as e:
            print("ANIME CAPTION ERR:", e)
            caption = build_default_caption(info, settings)
    else:
        caption = build_default_caption(info, settings)

    if font_style == "smallcaps":
        caption = to_small_caps(caption)

    if "‣ SYNOPSIS" in caption:
        head, rest = caption.split("‣ SYNOPSIS", 1)
        head = head.rstrip()
        body = rest.strip()
        if body.startswith("➟"):
            body = body[1:].strip()
        return (
            f"{html.escape(head)}\n"
            f"‣ <b>SYNOPSIS</b>\n"
            f"<blockquote>➟ {html.escape(body)}</blockquote>"
        )

    if "➟" in caption:
        head, body = caption.split("➟", 1)
        return f"{html.escape(head.rstrip())}\n<blockquote>➟ {html.escape(body.strip())}</blockquote>"

    return html.escape(caption)


def build_anime_keyboard(token, page, total, clean_mode=False):
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⟨ Prev", callback_data=f"anipage|{token}|{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="aninoop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("Next ⟩", callback_data=f"anipage|{token}|{page+1}"))

    return InlineKeyboardMarkup([
        nav,
        [
            InlineKeyboardButton(
                "🖼 Clean Art" if not clean_mode else "🎴 Card Art",
                callback_data=f"aniclean|{token}"
            ),
            InlineKeyboardButton("✅ Use This", callback_data=f"aniuse|{token}"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data=f"aniclear|{token}")],
    ])


def build_url_buttons(settings):
    rows = []
    for b in settings.get("buttons", []):
        if isinstance(b, dict) and b.get("text") and b.get("url"):
            rows.append([InlineKeyboardButton(b["text"], url=b["url"])])
    if not rows:
        rows = [[InlineKeyboardButton("No links in /animesettings", callback_data="aninoop")]]
    rows.append([InlineKeyboardButton("❌ Close", callback_data="aniclear|final")])
    return InlineKeyboardMarkup(rows)

@Client.on_message(filters.command("anime") & (filters.private | filters.group))
async def anime_cmd(client: Client, message: Message):
    cleanup_cache()
    ensure_fonts()
    if not message.from_user:
        return await message.reply_text("❌ User nahi mila.")

    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text("❌ Use:\n`/anime name`\n\nExample:\n`/anime naruto`")

    query = " ".join(message.command[1:]).strip()
    msg = await message.reply_text("🎴 Designing anime card...")

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
            item = select_anime(search.get("results", []), year)
            if not item:
                return await msg.edit_text("❌ Anime nahi mila.")

            media_type = item["media_type"]
            media_id = item["id"]
            details = await get_details(session, media_type, media_id)
            images_data = await get_images(session, media_type, media_id)

            posters = []
            if details.get("backdrop_path"):
                posters.append(tmdb_img_url(details["backdrop_path"]))
            for p in images_data.get("backdrops", [])[:15]:
                w, h = p.get("width") or 0, p.get("height") or 0
                if w and h and w < h:
                    continue
                url = tmdb_img_url(p.get("file_path"))
                if url and url not in posters:
                    posters.append(url)
            for p in images_data.get("posters", [])[:10]:
                url = tmdb_img_url(p.get("file_path"))
                if url and url not in posters:
                    posters.append(url)
            if not posters and details.get("poster_path"):
                posters.append(tmdb_img_url(details["poster_path"]))
            if not posters:
                return await msg.edit_text("❌ Images nahi mile.")

            genres = ", ".join([g["name"] for g in details.get("genres", [])][:4]) or "—"
            rating = details.get("vote_average")
            rating = f"{rating:.1f}" if rating else "N/A"

            if media_type == "tv":
                status_raw = details.get("status") or "—"
                if status_raw in ("Ended", "Canceled"):
                    status = "Finished"
                elif "Returning" in status_raw:
                    status = "Returning"
                else:
                    status = status_raw
                eps = details.get("number_of_episodes")
                episodes = str(eps) if eps else "—"
                seasons = details.get("number_of_seasons")
            else:
                status, episodes, seasons = "Released", "—", None

            story = (details.get("overview") or "No overview available.").strip()
            if len(story) > 320:
                story = story[:317] + "..."

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
                return await msg.edit_text("❌ Download fail.")

            settings = load_settings(user_id)
            photo = generate_anime_poster(base, info)
            caption = build_caption(info, settings)

            token = uuid.uuid4().hex[:12]
            ANIME_CACHE[token] = {
                "user_id": user_id,
                "info": info,
                "posters": posters,
                "page": 0,
                "clean_mode": False,
                "base_images": {0: base},
                "time": time.time(),
            }

            try:
                await msg.delete()
            except Exception:
                pass

            await client.send_photo(
                chat_id=message.chat.id,
                photo=fresh_photo(photo),
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=build_anime_keyboard(token, 0, len(posters), False)
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
        photo = make_clean_image(base) if clean_mode else generate_anime_poster(base, data["info"])
        settings = load_settings(user_id)

        await query.message.edit_media(
            media=InputMediaPhoto(
                media=fresh_photo(photo),
                caption=build_caption(data["info"], settings),
                parse_mode=ParseMode.HTML
            ),
            reply_markup=build_anime_keyboard(token, page, len(posters), clean_mode)
        )
    except Exception as e:
        print("ANIME RENDER ERR:", e)
        try:
            await query.answer("Update failed", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(cb_starts("anipage|"), group=-989)
async def ani_page(client: Client, query: CallbackQuery):
    try:
        _, token, page_s = query.data.split("|")
        page = int(page_s)
        data = ANIME_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]:
            await query.answer("Not yours", show_alert=True)
            raise StopPropagation
        if page < 0 or page >= len(data["posters"]):
            await query.answer("No more")
            raise StopPropagation
        data["page"] = page
        await query.answer(f"{page+1}")
        await render_anime(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI PAGE", e)
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
            await query.answer("Not yours", show_alert=True)
            raise StopPropagation
        data["clean_mode"] = not data.get("clean_mode", False)
        await query.answer("Clean" if data["clean_mode"] else "Card")
        await render_anime(client, query, data, token)
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI CLEAN", e)
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
            await query.answer("Not yours", show_alert=True)
            raise StopPropagation
        await query.message.edit_reply_markup(
            reply_markup=build_url_buttons(load_settings(data["user_id"]))
        )
        await query.answer("✅ Done")
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI USE", e)
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
            await query.message.edit_caption("Closed.")
        except Exception:
            pass
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.answer("Closed")
    except StopPropagation:
        raise
    except Exception as e:
        print("ANI CLEAR", e)
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
        "🎴 **ANIME SETTINGS** (sirf teri)\n\n"
        f"🎧 Audio: `{s.get('audio')}`\n"
        f"📺 Quality: `{s.get('pixels')}`\n"
        f"🔤 Font: `{s.get('font_style', 'normal')}`\n"
        f"📝 Caption: `{'Custom' if custom else 'Default'}`\n"
        f"🔗 Buttons: `{len(s.get('buttons', []))}`"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 CAPTION", callback_data="aset_caption"),
            InlineKeyboardButton("🎧 AUDIO", callback_data="aset_audio"),
        ],
        [
            InlineKeyboardButton("📺 QUALITY", callback_data="aset_pixels"),
            InlineKeyboardButton("🔗 BUTTONS", callback_data="aset_buttons"),
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
                "📝 Anime caption template bhej\n\n"
                "Placeholders:\n"
                "`{title} {year} {status} {episodes} {seasons} {rating} {rating_pct} {pixels} {audio} {genres} {story}`\n\n"
                f"**Example:**\n```\n{CAPTION_EXAMPLE}\n```\n\n"
                "Default: `default`\nCancel: /anicancel"
            )
        elif action == "aset_audio":
            ANIME_STATE[uid] = "wait_audio"
            await query.answer()
            await query.message.reply_text("🎧 Audio bhej\nEx: `Japanese | Hindi`\n/anicancel")
        elif action == "aset_pixels":
            ANIME_STATE[uid] = "wait_pixels"
            await query.answer()
            await query.message.reply_text("📺 Quality bhej\nEx: `720p | 1080p`\n/anicancel")
        elif action == "aset_buttons":
            ANIME_STATE[uid] = "wait_buttons"
            await query.answer()
            await query.message.reply_text("🔗 `Text - https://link.com`\nClear: `clear`\n/anicancel")
        elif action == "aset_font":
            s = load_settings(uid)
            cur = s.get("font_style", "normal")
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ NORMAL" if cur == "normal" else "NORMAL", callback_data="aset_font_normal"),
                InlineKeyboardButton("✅ SMALL CAPS" if cur == "smallcaps" else "SMALL CAPS", callback_data="aset_font_smallcaps"),
            ]])
            await query.answer()
            await query.message.edit_text(f"🔤 Font\nCurrent: `{cur}`", reply_markup=kb)
        elif action == "aset_font_normal":
            s = load_settings(uid)
            s["font_style"] = "normal"
            save_settings(uid, s)
            await query.answer("NORMAL ✅", show_alert=True)
        elif action == "aset_font_smallcaps":
            s = load_settings(uid)
            s["font_style"] = "smallcaps"
            save_settings(uid, s)
            await query.answer("SMALL CAPS ✅", show_alert=True)
        elif action == "aset_reset":
            save_settings(uid, DEFAULT_SETTINGS.copy())
            await query.answer("Reset ✅", show_alert=True)
        else:
            await query.answer()
    except Exception as e:
        print("ASET", e)
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
        await message.reply_text("✅ Anime caption save!")
    elif state == "wait_audio":
        s["audio"] = text
        save_settings(uid, s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ `{text}`")
    elif state == "wait_pixels":
        s["pixels"] = text
        save_settings(uid, s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ `{text}`")
    elif state == "wait_buttons":
        if text.lower() == "clear":
            s["buttons"] = []
        else:
            buttons = []
            for line in text.splitlines():
                if " - " in line:
                    a, b = line.split(" - ", 1)
                    if b.strip().startswith("http"):
                        buttons.append({"text": a.strip(), "url": b.strip()})
            s["buttons"] = buttons
        save_settings(uid, s)
        ANIME_STATE.pop(uid, None)
        await message.reply_text(f"✅ {len(s['buttons'])} buttons")


@Client.on_message(filters.command("anicancel") & (filters.private | filters.group))
async def anime_cancel(_, message: Message):
    if message.from_user:
        ANIME_STATE.pop(message.from_user.id, None)
    await message.reply_text("✅ Cleared.")

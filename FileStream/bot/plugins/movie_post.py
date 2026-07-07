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


async def create_poster(image_url, movie_data, color_name=None, branding=None, channel=None):
    img_bytes = await download_image(image_url)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    
    target = (1280, 720)
    r = img.size[0] / img.size[1]
    tr = target[0] / target[1]
    
    if r > tr:
        nh = target[1]
        nw = int(nh * r)
    else:
        nw = target[0]
        nh = int(nw / r)
    
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - target[0]) // 2
    top = (nh - target[1]) // 2
    img = img.crop((left, top, left + target[0], top + target[1]))
    
    dark_overlay = create_dark_overlay(target, opacity=90)
    img = Image.alpha_composite(img, dark_overlay)
    
    if color_name and color_name in COLORS:
        color_rgb = COLORS[color_name]
        left_gradient = create_left_gradient(target, color_rgb=color_rgb)
    else:
        left_gradient = create_left_gradient(target)
    
    img = Image.alpha_composite(img, left_gradient)
    
    draw = ImageDraw.Draw(img)
    
    title = movie_data.get("title") or movie_data.get("name") or "Unknown"
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres = movie_data.get("genres", [])
    if genres and isinstance(genres[0], dict):
        gn = [g.get("name", "") for g in genres[:2]]
    else:
        gn = genres[:2] if genres else []
    gstr = " & ".join(gn).upper() if gn else "MOVIE"
    
    runtime = movie_data.get("runtime") or 0
    if not runtime:
        et = movie_data.get("episode_run_time", [])
        runtime = et[0] if et else 0
    duration = f"{runtime} MIN" if runtime else ""
    
    overview = movie_data.get("overview", "")
    rating = movie_data.get("vote_average", 0)
    
    director = ""
    crew = movie_data.get("credits", {}).get("crew", [])
    for p in crew:
        if p.get("job") in ["Director", "Series Director"]:
            director = p.get("name", "").upper()
            break
    if not director:
        creators = movie_data.get("created_by", [])
        if creators:
            director = creators[0].get("name", "").upper()
    
    if branding:
        fw2 = get_font(18, bold=True)
        wb = draw.textbbox((0, 0), branding, font=fw2)
        ww = wb[2] - wb[0]
        wh = wb[3] - wb[1]
        wx = target[0] - ww - 30
        wy = 30
        padding = 8
        draw.rounded_rectangle(
            [(wx - padding, wy - padding), (wx + ww + padding, wy + wh + padding + 5)],
            radius=6, fill=(0, 0, 0, 150)
        )
        draw.text((wx + 1, wy + 1), branding, font=fw2, fill=(0, 0, 0, 200))
        draw.text((wx, wy), branding, font=fw2, fill=(255, 255, 255, 240))
    
    if channel:
        fc = get_font(18, bold=True)
        draw.text((30, 32), channel, font=fc, fill=(255, 255, 255, 220))
    
    if director:
        ff = get_font(13, bold=True)
        dc = COLORS[color_name] if color_name and color_name in COLORS else (46, 204, 113)
        draw.text((30, 220), "FILMED BY", font=ff, fill=(255, 255, 255, 200))
        b = draw.textbbox((0, 0), "FILMED BY", font=ff)
        fw = b[2] - b[0]
        draw.text((30 + fw + 10, 220), director[:30], font=ff, fill=dc)
    
    tu = title.upper()
    if len(tu) > 20:
        ts = 45
    elif len(tu) > 15:
        ts = 55
    else:
        ts = 65
    
    ft = get_font(ts, bold=True)
    draw.text((30, 255), tu, font=ft, fill=(255, 255, 255, 255))
    
    lc = COLORS[color_name] if color_name and color_name in COLORS else (46, 204, 113)
    tb = draw.textbbox((30, 255), tu, font=ft)
    lw = min(tb[2] - tb[0], 180)
    ly = tb[3] + 8
    draw.rectangle([(30, ly), (30 + lw, ly + 4)], fill=lc)
    
    fi = get_font(16, bold=True)
    it = year
    if gstr:
        it += f"  •  {gstr}"
    if duration:
        it += f"  •  {duration}"
    
    iy = ly + 20
    draw.text((30, iy), it, font=fi, fill=(220, 220, 220, 255))
    
    if overview:
        fs = get_font(13)
        mc = 70
        words = overview.split()
        lines = []
        cl = ""
        for w in words:
            if len(cl) + len(w) + 1 <= mc:
                cl += (" " if cl else "") + w
            else:
                lines.append(cl)
                cl = w
                if len(lines) >= 3:
                    break
        if cl and len(lines) < 3:
            lines.append(cl)
        if len(lines) == 3 and len(overview) > 200:
            lines[2] = lines[2][:65] + "..."
        
        sy = iy + 30
        for line in lines:
            draw.text((30, sy), line, font=fs, fill=(210, 210, 210, 230))
            sy += 20
    
    by = target[1] - 100
    bw = 200
    bh = 50
    
    bc = COLORS[color_name] if color_name and color_name in COLORS else (231, 76, 60)
    
    draw.rounded_rectangle([(30, by), (30 + bw, by + bh)], radius=8, fill=bc)
    
    fb = get_font(18, bold=True)
    bt = "▶ WATCH NOW"
    b2 = draw.textbbox((0, 0), bt, font=fb)
    btw = b2[2] - b2[0]
    btx = 30 + (bw - btw) // 2
    bty = by + (bh - (b2[3] - b2[1])) // 2 - 4
    draw.text((btx, bty), bt, font=fb, fill=(255, 255, 255, 255))
    
    ix = 30 + bw + 15
    iw = 170
    
    draw.rounded_rectangle(
        [(ix, by), (ix + iw, by + bh)],
        radius=8, fill=(20, 20, 20, 230),
        outline=(255, 200, 0, 255), width=2
    )
    
    fst = get_font(22, bold=True)
    draw.text((ix + 15, by + 10), "✦", font=fst, fill=(255, 200, 0, 255))
    
    fr = get_font(16, bold=True)
    rt = f"{rating:.1f} IMDb" if rating else "N/A IMDb"
    draw.text((ix + 50, by + 16), rt, font=fr, fill=(255, 255, 255, 255))
    
    final = img.convert("RGB")
    out = io.BytesIO()
    final.save(out, format="JPEG", quality=95)
    out.seek(0)
    return out


def format_caption(movie_data, settings):
    title = movie_data.get("title") or movie_data.get("name") or "Unknown"
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres = movie_data.get("genres", [])
    if genres and isinstance(genres[0], dict):
        gn = [g.get("name", "") for g in genres]
    else:
        gn = genres if genres else []
    gstr = " • ".join(gn) if gn else "N/A"
    
    rating = movie_data.get("vote_average", 0)
    overview = movie_data.get("overview", "")
    
    template = settings.get("caption", DEFAULT_CAPTION)
    
    try:
        return template.format(
            title=title, year=year, genres=gstr,
            audio="Hindi & English", quality="480p, 720p, 1080p",
            rating=f"{rating:.1f}" if rating else "N/A",
            overview=overview[:200] + "..." if len(overview) > 200 else overview,
        )
    except:
        return f"<b>{title} ({year})</b>\n\n➡ <b>Genres:</b> <code>{gstr}</code>"


def build_control_buttons(token, idx=0, total=1):
    buttons = []
    
    if total > 1:
        buttons.append([
            InlineKeyboardButton("⬅️ PREV", callback_data=f"mvnav|{token}|prev"),
            InlineKeyboardButton(f"{idx + 1}/{total}", callback_data=f"mvnav|{token}|info"),
            InlineKeyboardButton("NEXT ➡️", callback_data=f"mvnav|{token}|next"),
        ])
    
    buttons.append([
        InlineKeyboardButton("🔴", callback_data=f"mvcolor|{token}|red"),
        InlineKeyboardButton("🟠", callback_data=f"mvcolor|{token}|orange"),
        InlineKeyboardButton("🟡", callback_data=f"mvcolor|{token}|yellow"),
        InlineKeyboardButton("🟢", callback_data=f"mvcolor|{token}|green"),
    ])
    
    buttons.append([
        InlineKeyboardButton("🔵", callback_data=f"mvcolor|{token}|blue"),
        InlineKeyboardButton("🟣", callback_data=f"mvcolor|{token}|purple"),
        InlineKeyboardButton("⚫", callback_data=f"mvcolor|{token}|black"),
        InlineKeyboardButton("🔄 Reset", callback_data=f"mvcolor|{token}|none"),
    ])
    
    buttons.append([
        InlineKeyboardButton("🇬🇧 English", callback_data=f"mvlang|{token}|en"),
        InlineKeyboardButton("🇮🇳 हिंदी", callback_data=f"mvlang|{token}|hi"),
    ])
    
    buttons.append([
        InlineKeyboardButton("✅ USE NORMAL", callback_data=f"mvuse|{token}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"mvcancel|{token}"),
    ])
    
    return InlineKeyboardMarkup(buttons)


def build_download_buttons(settings):
    buttons = []
    ub = settings.get("buttons", DEFAULT_BUTTONS)
    
    for i in range(0, len(ub), 2):
        row = [InlineKeyboardButton(ub[i]["text"], url=ub[i]["url"])]
        if i + 1 < len(ub):
            row.append(InlineKeyboardButton(ub[i + 1]["text"], url=ub[i + 1]["url"]))
        buttons.append(row)
    
    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["movie", "post", "tv"]))
async def movie_handler(client, message):
    cleanup_cache()
    
    if len(message.command) < 2:
        return await message.reply_text(
            "🎬 <b>Movie Post Generator</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/movie the witcher 2019</code>\n"
            "<code>/tv breaking bad</code>\n\n"
            "<b>Settings:</b> <code>/postsettings</code>"
        )
    
    query_text = " ".join(message.command[1:])
    ym = re.search(r"\b(19|20)\d{2}\b", query_text)
    year = ym.group() if ym else None
    query = query_text.replace(year, "").strip() if year else query_text
    
    msg = await message.reply_text(f"🔍 <b>Searching:</b> <code>{query_text}</code>")
    
    try:
        results = await search_movie(query, year)
        
        if not results:
            return await msg.edit_text("❌ <b>Not found</b>")
        
        movie = results[0]
        if year:
            for r in results:
                d = r.get("release_date") or r.get("first_air_date", "")
                if d.startswith(year):
                    movie = r
                    break
        
        mtype = movie.get("media_type", "movie")
        details = await get_details(movie["id"], mtype)
        images = await get_images(movie["id"], mtype)
        
        image_urls = []
        if details.get("backdrop_path"):
            image_urls.append(TMDB_IMG + details["backdrop_path"])
        for bd in images.get("backdrops", [])[:20]:
            url = TMDB_IMG + bd["file_path"]
            if url not in image_urls:
                image_urls.append(url)
        
        if not image_urls:
            return await msg.edit_text("❌ <b>No images</b>")
        
        token = uuid.uuid4().hex[:10]
        POST_CACHE[token] = {
            "images": image_urls,
            "current_index": 0,
            "movie_data": details,
            "movie_id": movie["id"],
            "media_type": mtype,
            "selected_color": None,
            "language": "en",
            "user_id": message.from_user.id,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "time": time.time()
        }
        
        settings = get_user_settings(message.from_user.id)
        
        await msg.edit_text("🎨 <b>Creating poster...</b>")
        
        poster = await create_poster(
            image_urls[0], details,
            color_name=None,
            branding=settings["branding"],
            channel=settings.get("channel", DEFAULT_CHANNEL)
        )
        
        caption = format_caption(details, settings)
        
        await msg.delete()
        
        await client.send_photo(
            chat_id=message.chat.id,
            photo=poster,
            caption=caption,
            reply_markup=build_control_buttons(token, 0, len(image_urls)),
            reply_to_message_id=message.id,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        await msg.edit_text(f"❌ <b>Error</b>\n\n<code>{str(e)[:400]}</code>")


@Client.on_callback_query(cb_starts("mvnav|"), group=-999)
async def nav_cb(client, query):
    try:
        _, token, action = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired!", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        if action == "info":
            return await query.answer(f"{data['current_index'] + 1}/{len(data['images'])}")
        
        total = len(data["images"])
        if action == "next":
            data["current_index"] = (data["current_index"] + 1) % total
        else:
            data["current_index"] = (data["current_index"] - 1) % total
        
        await query.answer(f"Loading {data['current_index'] + 1}...")
        
        settings = get_user_settings(query.from_user.id)
        poster = await create_poster(
            data["images"][data["current_index"]],
            data["movie_data"],
            color_name=data.get("selected_color"),
            branding=settings["branding"],
            channel=settings.get("channel", DEFAULT_CHANNEL)
        )
        caption = format_caption(data["movie_data"], settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_control_buttons(token, data["current_index"], total)
        )
    except Exception as e:
        print(f"Nav: {e}")
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("mvcolor|"), group=-999)
async def color_cb(client, query):
    try:
        _, token, color = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired!", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        
        if color == "none":
            data["selected_color"] = None
            await query.answer("Color reset")
        else:
            data["selected_color"] = color
            await query.answer(f"Applied {color}")
        
        settings = get_user_settings(query.from_user.id)
        poster = await create_poster(
            data["images"][data["current_index"]],
            data["movie_data"],
            color_name=data.get("selected_color"),
            branding=settings["branding"],
            channel=settings.get("channel", DEFAULT_CHANNEL)
        )
        caption = format_caption(data["movie_data"], settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_control_buttons(token, data["current_index"], len(data["images"]))
        )
    except Exception as e:
        print(f"Color: {e}")
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("mvlang|"), group=-999)
async def lang_cb(client, query):
    try:
        _, token, lang = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired!", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        
        lang_name = "हिंदी" if lang == "hi" else "English"
        await query.answer(f"Loading in {lang_name}...")
        
        data["language"] = lang
        new_details = await get_details(data["movie_id"], data["media_type"], lang=lang)
        data["movie_data"] = new_details
        
        settings = get_user_settings(query.from_user.id)
        
        if lang == "hi":
            settings["caption"] = DEFAULT_CAPTION_HINDI
        else:
            settings["caption"] = DEFAULT_CAPTION
        
        poster = await create_poster(
            data["images"][data["current_index"]],
            new_details,
            color_name=data.get("selected_color"),
            branding=settings["branding"],
            channel=settings.get("channel", DEFAULT_CHANNEL)
        )
        caption = format_caption(new_details, settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_control_buttons(token, data["current_index"], len(data["images"]))
        )
    except Exception as e:
        print(f"Lang: {e}")
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("mvuse|"), group=-999)
async def use_cb(client, query):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired!", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        
        await query.answer("✅ Finalized!")
        
        settings = get_user_settings(query.from_user.id)
        
        poster = await create_poster(
            data["images"][data["current_index"]],
            data["movie_data"],
            color_name=None,
            branding=None,
            channel=None
        )
        
        caption = format_caption(data["movie_data"], settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_download_buttons(settings)
        )
        
        POST_CACHE.pop(token, None)
    except Exception as e:
        print(f"Use: {e}")
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("mvcancel|"), group=-999)
async def cancel_cb(client, query):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if data and query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        POST_CACHE.pop(token, None)
        await query.answer("Cancelled")
        await query.message.delete()
    except:
        pass
    finally:
        raise StopPropagation

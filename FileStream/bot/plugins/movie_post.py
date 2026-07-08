import os
import io
import re
import uuid
import time
import asyncio
import aiohttp
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)


TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

DEFAULT_BRANDING = "@Patrick_Botz"
DEFAULT_CHANNEL = "@NOVA_FLIX"
DEFAULT_CAPTION = "<b>{title} ({year})</b>\n\n➡ <b>Audio:</b> <code>Hindi</code>\n➡ <b>Quality:</b> <code>480p, 720p, 1080p</code>\n➡ <b>Genres:</b> <code>{genres}</code>"
DEFAULT_BUTTON_TEXT = "🔽 Download"
DEFAULT_BUTTON_URL = "https://t.me/Patrick_Botz"

COLORS = {
    "red": (231, 76, 60),
    "orange": (230, 126, 34),
    "yellow": (241, 196, 15),
    "green": (46, 204, 113),
    "blue": (52, 152, 219),
    "purple": (155, 89, 182),
    "black": (30, 30, 30),
    "white": (200, 200, 200),
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
            "button_text": DEFAULT_BUTTON_TEXT,
            "button_url": DEFAULT_BUTTON_URL,
        }
    return USER_SETTINGS[user_id]


async def search_movie(query, year=None):
    async with aiohttp.ClientSession() as session:
        params = {"api_key": TMDB_API, "query": query}
        if year:
            params["year"] = year
        async with session.get(f"{TMDB_BASE}/search/multi", params=params) as resp:
            data = await resp.json()
            return [r for r in data.get("results", []) if r.get("media_type") in ["movie", "tv"]]


async def get_movie_details(media_id, media_type):
    async with aiohttp.ClientSession() as session:
        params = {"api_key": TMDB_API, "append_to_response": "credits"}
        async with session.get(f"{TMDB_BASE}/{media_type}/{media_id}", params=params) as resp:
            return await resp.json()


async def get_movie_images(media_id, media_type):
    async with aiohttp.ClientSession() as session:
        params = {"api_key": TMDB_API, "include_image_language": "en,null,hi"}
        async with session.get(f"{TMDB_BASE}/{media_type}/{media_id}/images", params=params) as resp:
            return await resp.json()


async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()


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


def create_gradient(size, direction="left"):
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    w, h = size
    if direction == "left":
        for x in range(w):
            alpha = max(0, min(255, int(255 * (1 - x / (w * 0.7)))))
            draw.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha))
    else:
        for y in range(h):
            alpha = max(0, min(255, int(255 * (y / h))))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    return gradient


async def create_poster(image_url, movie_data, color_name=None, channel=None, branding=None):
    img_bytes = await download_image(image_url)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    
    target_size = (1280, 720)
    ratio = img.size[0] / img.size[1]
    target_ratio = target_size[0] / target_size[1]
    
    if ratio > target_ratio:
        new_h = target_size[1]
        new_w = int(new_h * ratio)
    else:
        new_w = target_size[0]
        new_h = int(new_w / ratio)
    
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_size[0]) // 2
    top = (new_h - target_size[1]) // 2
    img = img.crop((left, top, left + target_size[0], top + target_size[1]))
    
    if color_name and color_name in COLORS:
        c = COLORS[color_name]
        overlay = Image.new("RGBA", target_size, (c[0], c[1], c[2], 100))
        img = Image.alpha_composite(img, overlay)
    
    img = Image.alpha_composite(img, create_gradient(target_size, "left"))
    img = Image.alpha_composite(img, create_gradient(target_size, "bottom"))
    
    draw = ImageDraw.Draw(img)
    
    title = movie_data.get("title") or movie_data.get("name") or "Unknown"
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres = movie_data.get("genres", [])
    if genres and isinstance(genres[0], dict):
        gnames = [g.get("name", "") for g in genres[:2]]
    else:
        gnames = genres[:2] if genres else []
    genres_str = " & ".join(gnames).upper() if gnames else "MOVIE"
    
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
    
    if channel:
        font_ch = get_font(22, bold=True)
        draw.rectangle([(30, 30), (60, 55)], fill=(255, 255, 255, 30))
        draw.text((70, 32), channel, font=font_ch, fill=(255, 255, 255, 255))
    
    if director:
        font_fb = get_font(16, bold=True)
        dc = COLORS[color_name] if color_name and color_name in COLORS else (46, 204, 113)
        draw.text((30, 200), "FILMED BY", font=font_fb, fill=(255, 255, 255, 200))
        bbox = draw.textbbox((0, 0), "FILMED BY", font=font_fb)
        fw = bbox[2] - bbox[0]
        draw.text((30 + fw + 10, 200), director[:30], font=font_fb, fill=dc)
    
    title_upper = title.upper()
    if len(title_upper) > 20:
        ts = 55
    elif len(title_upper) > 15:
        ts = 70
    else:
        ts = 85
    
    font_title = get_font(ts, bold=True)
    draw.text((30, 240), title_upper, font=font_title, fill=(255, 255, 255, 255))
    
    lc = COLORS[color_name] if color_name and color_name in COLORS else (46, 204, 113)
    tbbox = draw.textbbox((30, 240), title_upper, font=font_title)
    lw = min(tbbox[2] - tbbox[0], 200)
    ly = tbbox[3] + 10
    draw.rectangle([(30, ly), (30 + lw, ly + 4)], fill=lc)
    
    font_info = get_font(20, bold=True)
    info_text = year
    if genres_str:
        info_text += f"  •  {genres_str}"
    if duration:
        info_text += f"  •  {duration}"
    
    iy = ly + 25
    draw.text((30, iy), info_text, font=font_info, fill=(220, 220, 220, 255))
    
    if overview:
        font_story = get_font(16)
        max_chars = 65
        words = overview.split()
        lines = []
        cl = ""
        for w in words:
            if len(cl) + len(w) + 1 <= max_chars:
                cl += (" " if cl else "") + w
            else:
                lines.append(cl)
                cl = w
                if len(lines) >= 2:
                    break
        if cl and len(lines) < 2:
            lines.append(cl)
        if len(lines) == 2 and len(overview) > 130:
            lines[1] = lines[1][:60] + "..."
        
        sy = iy + 40
        for line in lines:
            draw.text((30, sy), line, font=font_story, fill=(200, 200, 200, 220))
            sy += 22
    
    by = target_size[1] - 120
    bw = 200
    bh = 55
    
    bc = COLORS[color_name] if color_name and color_name in COLORS else (231, 76, 60)
    
    draw.rounded_rectangle([(30, by), (30 + bw, by + bh)], radius=8, fill=bc)
    
    font_btn = get_font(20, bold=True)
    btn_text = "▶ WATCH NOW"
    bbox2 = draw.textbbox((0, 0), btn_text, font=font_btn)
    btw = bbox2[2] - bbox2[0]
    btx = 30 + (bw - btw) // 2
    bty = by + (bh - (bbox2[3] - bbox2[1])) // 2 - 5
    draw.text((btx, bty), btn_text, font=font_btn, fill=(255, 255, 255, 255))
    
    ix = 30 + bw + 15
    iw = 130
    
    draw.rounded_rectangle([(ix, by), (ix + iw, by + bh)], radius=8, fill=(20, 20, 20, 220), outline=(255, 200, 0, 255), width=1)
    
    font_star = get_font(24, bold=True)
    draw.text((ix + 15, by + 12), "✦", font=font_star, fill=(255, 200, 0, 255))
    
    font_r = get_font(18, bold=True)
    rt = f"{rating:.1f} IMDb" if rating else "N/A IMDb"
    draw.text((ix + 45, by + 18), rt, font=font_r, fill=(255, 255, 255, 255))
    
    if branding:
        font_wm = get_font(20, bold=True)
        wbbox = draw.textbbox((0, 0), branding, font=font_wm)
        ww = wbbox[2] - wbbox[0]
        wx = (target_size[0] - ww) // 2
        wy = target_size[1] - 40
        draw.text((wx + 2, wy + 2), branding, font=font_wm, fill=(0, 0, 0, 200))
        draw.text((wx, wy), branding, font=font_wm, fill=(255, 255, 255, 200))
    
    final = img.convert("RGB")
    output = io.BytesIO()
    final.save(output, format="JPEG", quality=95)
    output.seek(0)
    return output


def format_caption(template, movie_data):
    title = movie_data.get("title") or movie_data.get("name") or "Unknown"
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres = movie_data.get("genres", [])
    if genres and isinstance(genres[0], dict):
        gnames = [g.get("name", "") for g in genres]
    else:
        gnames = genres if genres else []
    gs = " • ".join(gnames) if gnames else "N/A"
    
    overview = movie_data.get("overview", "")
    rating = movie_data.get("vote_average", 0)
    
    return template.format(
        title=title,
        year=year,
        genres=gs,
        overview=overview[:200] + "..." if len(overview) > 200 else overview,
        rating=f"{rating:.1f}" if rating else "N/A",
        audio="Hindi & English",
        quality="480p, 720p, 1080p",
    )


def build_buttons(token, idx=0, total=1):
    buttons = []
    if total > 1:
        buttons.append([
            InlineKeyboardButton("⬅️ PREV", callback_data=f"postnav|{token}|prev"),
            InlineKeyboardButton(f"{idx + 1}/{total}", callback_data=f"postnav|{token}|info"),
            InlineKeyboardButton("NEXT ➡️", callback_data=f"postnav|{token}|next"),
        ])
    buttons.append([
        InlineKeyboardButton("🔴", callback_data=f"postcolor|{token}|red"),
        InlineKeyboardButton("🟠", callback_data=f"postcolor|{token}|orange"),
        InlineKeyboardButton("🟡", callback_data=f"postcolor|{token}|yellow"),
        InlineKeyboardButton("🟢", callback_data=f"postcolor|{token}|green"),
    ])
    buttons.append([
        InlineKeyboardButton("🔵", callback_data=f"postcolor|{token}|blue"),
        InlineKeyboardButton("🟣", callback_data=f"postcolor|{token}|purple"),
        InlineKeyboardButton("⚫", callback_data=f"postcolor|{token}|black"),
        InlineKeyboardButton("⚪", callback_data=f"postcolor|{token}|white"),
    ])
    buttons.append([InlineKeyboardButton("✅ USE NORMAL", callback_data=f"postuse|{token}|normal")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"postcancel|{token}")])
    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["movie", "post", "tv"]))
async def movie_handler(client, message):
    cleanup_cache()
    
    if len(message.command) < 2:
        return await message.reply_text("🎬 **Usage:** `/movie the witcher 2019`")
    
    query_text = " ".join(message.command[1:])
    ym = re.search(r"\b(19|20)\d{2}\b", query_text)
    year = ym.group() if ym else None
    query = query_text.replace(year, "").strip() if year else query_text
    
    msg = await message.reply_text(f"🔍 **Searching:** `{query_text}`")
    
    try:
        results = await search_movie(query, year)
        if not results:
            return await msg.edit_text("❌ Not found")
        
        movie = results[0]
        if year:
            for r in results:
                d = r.get("release_date") or r.get("first_air_date", "")
                if d.startswith(year):
                    movie = r
                    break
        
        details = await get_movie_details(movie["id"], movie.get("media_type", "movie"))
        images = await get_movie_images(movie["id"], movie.get("media_type", "movie"))
        
        image_urls = []
        if details.get("backdrop_path"):
            image_urls.append(TMDB_IMG + details["backdrop_path"])
        for bd in images.get("backdrops", [])[:20]:
            url = TMDB_IMG + bd["file_path"]
            if url not in image_urls:
                image_urls.append(url)
        
        if not image_urls:
            return await msg.edit_text("❌ No images")
        
        token = uuid.uuid4().hex[:10]
        POST_CACHE[token] = {
            "images": image_urls,
            "current_index": 0,
            "movie_data": details,
            "selected_color": None,
            "user_id": message.from_user.id,
            "time": time.time()
        }
        
        settings = get_user_settings(message.from_user.id)
        poster = await create_poster(image_urls[0], details, None, settings["channel"], settings["branding"])
        caption = format_caption(settings["caption"], details)
        
        await msg.delete()
        await client.send_photo(
            chat_id=message.chat.id,
            photo=poster,
            caption=caption,
            reply_markup=build_buttons(token, 0, len(image_urls)),
            reply_to_message_id=message.id,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit_text(f"❌ **Error**\n\n`{str(e)[:400]}`")


@Client.on_callback_query(cb_starts("postnav|"), group=-999)
async def nav_cb(client, query):
    try:
        _, token, action = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not yours", show_alert=True)
        if action == "info":
            return await query.answer(f"{data['current_index'] + 1}/{len(data['images'])}")
        
        total = len(data["images"])
        if action == "next":
            data["current_index"] = (data["current_index"] + 1) % total
        else:
            data["current_index"] = (data["current_index"] - 1) % total
        
        await query.answer(f"Loading {data['current_index'] + 1}")
        settings = get_user_settings(query.from_user.id)
        poster = await create_poster(
            data["images"][data["current_index"]],
            data["movie_data"],
            data.get("selected_color"),
            settings["channel"],
            settings["branding"]
        )
        caption = format_caption(settings["caption"], data["movie_data"])
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_buttons(token, data["current_index"], total)
        )
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postcolor|"), group=-999)
async def color_cb(client, query):
    try:
        _, token, color = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not yours", show_alert=True)
        
        await query.answer(f"Applied {color}")
        data["selected_color"] = color
        settings = get_user_settings(query.from_user.id)
        poster = await create_poster(
            data["images"][data["current_index"]],
            data["movie_data"],
            color,
            settings["channel"],
            settings["branding"]
        )
        caption = format_caption(settings["caption"], data["movie_data"])
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_buttons(token, data["current_index"], len(data["images"]))
        )
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postuse|"), group=-999)
async def use_cb(client, query):
    try:
        _, token, _ = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not yours", show_alert=True)
        
        await query.answer("Finalized")
        settings = get_user_settings(query.from_user.id)
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton(settings["button_text"], url=settings["button_url"])
        ]])
        await query.message.edit_reply_markup(btn)
        POST_CACHE.pop(token, None)
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postcancel|"), group=-999)
async def cancel_cb(client, query):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if data and query.from_user.id != data["user_id"]:
            return await query.answer("Not yours", show_alert=True)
        POST_CACHE.pop(token, None)
        await query.answer("Cancelled")
        await query.message.delete()
    finally:
        raise StopPropagation

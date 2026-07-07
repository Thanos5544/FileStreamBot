import os
import io
import re
import uuid
import time
import aiohttp
import copy
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

# --- CONFIGURATION ---
TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

DEFAULT_BRANDING = "@Patrick_Botz"
DEFAULT_CHANNEL = "@Patrick_Botz"
DEFAULT_CAPTION = "<b>{title} ({year})</b>\n\n➡ <b>Audio:</b> <code>Hindi</code>\n➡ <b>Quality:</b> <code>480p, 720p, 1080p</code>\n➡ <b>Genres:</b> <code>{genres}</code>"

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
    "black": (30, 30, 30), "white": (240, 240, 240),
}

POST_CACHE = {}
USER_SETTINGS = {}

# --- HELPERS ---
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
            "buttons": copy.deepcopy(DEFAULT_BUTTONS),
        }
    return USER_SETTINGS[user_id]

async def search_movie(query, year=None):
    async with aiohttp.ClientSession() as s:
        p = {"api_key": TMDB_API, "query": query}
        if year: p["year"] = year
        async with s.get(f"{TMDB_BASE}/search/multi", params=p) as r:
            d = await r.json()
            return [x for x in d.get("results", []) if x.get("media_type") in ["movie", "tv"]]

async def get_details(mid, mtype):
    async with aiohttp.ClientSession() as s:
        p = {"api_key": TMDB_API, "append_to_response": "credits"}
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

def get_font(size, bold=True):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: continue
    return ImageFont.load_default()

# --- POSTIFY RENDERING ENGINE ---
def apply_postify_gradient(size, color_name):
    w, h = size
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    if color_name == "normal" or color_name not in COLORS:
        # Light black gradient for "USE NORMAL" look
        for x in range(int(w * 0.5)):
            alpha = int(160 * (1 - x / (w * 0.5)))
            draw.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha))
    else:
        # Color Tinted Black Gradient (Postify style)
        rgb = COLORS[color_name]
        tint_color = (int(rgb[0]*0.4), int(rgb[1]*0.4), int(rgb[2]*0.4))
        for x in range(int(w * 0.5)):
            alpha = int(200 * (1 - x / (w * 0.5)))
            draw.line([(x, 0), (x, h)], fill=(*tint_color, alpha))
    return overlay

async def create_poster(image_url, movie_data, color_name=None, channel=None):
    img_bytes = await download_image(image_url)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    
    # Professional fit to avoid face cropping
    img = ImageOps.fit(img, (1280, 720), method=Image.LANCZOS)
    
    # Postify Color Tuning
    img = ImageEnhance.Contrast(img).enhance(1.2)
    img = ImageEnhance.Color(img).enhance(1.3)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    
    # Left-side only gradient
    gradient = apply_postify_gradient((1280, 720), color_name)
    img = Image.alpha_composite(img, gradient)
    
    draw = ImageDraw.Draw(img)
    title = (movie_data.get("title") or movie_data.get("name") or "Unknown").upper()
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres_list = movie_data.get("genres", [])
    gn = [g.get("name", "") for g in genres_list[:3]] if genres_list and isinstance(genres_list[0], dict) else genres_list[:3]
    gstr = " • ".join(gn).upper() if gn else "MOVIE"
    
    runtime = movie_data.get("runtime") or (movie_data.get("episode_run_time", [0])[0])
    duration = f"{runtime} MIN" if runtime else ""
    
    director = ""
    crew = movie_data.get("credits", {}).get("crew", [])
    for p in crew:
        if p.get("job") in ["Director", "Series Director"]:
            director = p.get("name", "").upper()
            break
    if not director:
        creators = movie_data.get("created_by", [])
        if creators: director = creators[0].get("name", "").upper()

    if director:
        f_small = get_font(14, bold=False)
        draw.text((40, 60), "FILMED BY", font=f_small, fill=(200, 200, 200, 200))
        draw.text((125, 60), director[:40], font=get_font(14, bold=True), fill=(255, 255, 255, 255))

    ts = 70 if len(title) < 15 else 55 if len(title) < 25 else 45
    draw.text((40, 90), title, font=get_font(ts, bold=True), fill=(255, 255, 255, 255))
    
    sub_text = f"{year}  •  {gstr}" + (f"  •  {duration}" if duration else "")
    draw.text((40, 90 + ts + 10), sub_text, font=get_font(18, bold=False), fill=(200, 200, 200, 220))
    
    overview = movie_data.get("overview", "")
    if overview:
        f_ov = get_font(16, bold=False)
        words = overview.split()
        lines, curr = [], ""
        for w in words:
            if len(curr) + len(w) < 65: curr += (" " if curr else "") + w
            else:
                lines.append(curr); curr = w
                if len(lines) >= 3: break
        if curr and len(lines) < 3: lines.append(curr)
        oy = 90 + ts + 50
        for line in lines:
            draw.text((40, oy), line, font=f_ov, fill=(180, 180, 180, 200))
            oy += 25

    # Buttons
    btn_color = (74, 0, 224, 255) if color_name == "normal" else (COLORS.get(color_name, (74, 0, 224)) + (255,))
    draw.rounded_rectangle([(40, 600), (220, 650)], radius=12, fill=btn_color)
    f_btn = get_font(18, bold=True)
    bt_text = "▶ WATCH NOW"
    tw = draw.textbbox((0,0), bt_text, font=f_btn)[2] - draw.textbbox((0,0), bt_text, font=f_btn)[0]
    draw.text((40 + (180 - tw)//2, 614), bt_text, font=f_btn, fill=(255, 255, 255, 255))
    
    rating = movie_data.get("vote_average", 0)
    draw.rounded_rectangle([(235, 600), (355, 650)], radius=12, fill=(20, 20, 20, 230), outline=(255, 193, 7, 255), width=2)
    rt_text = f"★ {rating:.1f} IMDb"
    rtw = draw.textbbox((0,0), rt_text, font=f_btn)[2] - draw.textbbox((0,0), rt_text, font=f_btn)[0]
    draw.text((235 + (120 - rtw)//2, 614), rt_text, font=f_btn, fill=(255, 193, 7, 255))

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
    gn = [g.get("name", "") for g in genres] if genres and isinstance(genres[0], dict) else genres
    gstr = " • ".join(gn) if gn else "N/A"
    template = settings.get("caption", DEFAULT_CAPTION)
    try:
        return template.format(title=title, year=year, genres=gstr, audio="Hindi", quality="480p, 720p, 1080p")
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
        InlineKeyboardButton("⚪", callback_data=f"mvcolor|{token}|white"),
    ])
    buttons.append([InlineKeyboardButton("✨ USE NORMAL", callback_data=f"mvcolor|{token}|normal")])
    buttons.append([InlineKeyboardButton("✅ USE THIS", callback_data=f"mvuse|{token}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"mvcancel|{token}")])
    return InlineKeyboardMarkup(buttons)

def build_download_buttons(settings):
    buttons = []
    ub = settings.get("buttons", DEFAULT_BUTTONS)
    for i in range(0, len(ub), 2):
        row = [InlineKeyboardButton(ub[i]["text"], url=ub[i]["url"])]
        if i + 1 < len(ub): row.append(InlineKeyboardButton(ub[i + 1]["text"], url=ub[i + 1]["url"]))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command(["movie", "post", "tv"]))
async def movie_handler(client, message):
    cleanup_cache()
    if len(message.command) < 2:
        return await message.reply_text("🎬 <b>Usage:</b> <code>/movie the witcher 2019</code>")
    
    query_text = " ".join(message.command[1:])
    ym = re.search(r"\b(19|20)\d{2}\b", query_text)
    year = ym.group() if ym else None
    query = query_text.replace(year, "").strip() if year else query_text
    
    msg = await message.reply_text(f"🔍 <b>Searching:</b> <code>{query_text}</code>")
    try:
        results = await search_movie(query, year)
        if not results: return await msg.edit_text("❌ <b>Not found</b>")
        
        movie = results[0]
        mtype = movie.get("media_type", "movie")
        details = await get_details(movie["id"], mtype)
        images = await get_images(movie["id"], mtype)
        
        image_urls = []
        if details.get("backdrop_path"): image_urls.append(TMDB_IMG + details["backdrop_path"])
        for bd in images.get("backdrops", [])[:20]:
            url = TMDB_IMG + bd["file_path"]
            if url not in image_urls: image_urls.append(url)
        
        if not image_urls: return await msg.edit_text("❌ <b>No images</b>")
        
        token = uuid.uuid4().hex[:10]
        POST_CACHE[token] = {
            "images": image_urls, "current_index": 0, "movie_data": details,
            "selected_color": "normal", "user_id": message.from_user.id,
            "chat_id": message.chat.id, "time": time.time()
        }
        
        settings = get_user_settings(message.from_user.id)
        await msg.edit_text("🎨 <b>Creating Postify Poster...</b>")
        
        poster = await create_poster(image_urls[0], details, color_name="normal", channel=settings.get("channel"))
        caption = format_caption(details, settings)
        
        await msg.delete()
        await client.send_photo(
            chat_id=message.chat.id, photo=poster, caption=caption,
            reply_markup=build_control_buttons(token, 0, len(image_urls)),
            reply_to_message_id=message.id, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit_text(f"❌ <b>Error:</b> <code>{e}</code>")

@Client.on_callback_query(cb_starts("mvnav|"), group=-999)
async def nav_cb(client, query):
    try:
        _, token, action = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]: return await query.answer("Expired!")
        
        total = len(data["images"])
        if action == "prev": data["current_index"] = (data["current_index"] - 1) % total
        elif action == "next": data["current_index"] = (data["current_index"] + 1) % total
        else: return await query.answer()
        
        settings = get_user_settings(query.from_user.id)
        poster = await create_poster(data["images"][data["current_index"]], data["movie_data"], data["selected_color"], settings.get("channel"))
        caption = format_caption(data["movie_data"], settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_control_buttons(token, data["current_index"], total)
        )
        await query.answer()
    except Exception as e: print(f"Nav Error: {e}")
    finally: raise StopPropagation

@Client.on_callback_query(cb_starts("mvcolor|"), group=-999)
async def color_cb(client, query):
    try:
        _, token, color = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]: return await query.answer("Expired!")
        
        data["selected_color"] = color
        await query.answer(f"Applied {color}")
        
        settings = get_user_settings(query.from_user.id)
        poster = await create_poster(data["images"][data["current_index"]], data["movie_data"], color, settings.get("channel"))
        caption = format_caption(data["movie_data"], settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(media=poster, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=build_control_buttons(token, data["current_index"], len(data["images"]))
        )
    except Exception as e: print(f"Color Error: {e}")
    finally: raise StopPropagation

@Client.on_callback_query(cb_starts("mvuse|"), group=-999)
async def use_cb(client, query):
    try:
        _, token = query.data.split("|")
        data = POST_CACHE.get(token)
        if not data or query.from_user.id != data["user_id"]: return await query.answer("Expired!")
        
        await query.answer("✅ Finalized!")
        settings = get_user_settings(query.from_user.id)
        await query.message.edit_reply_markup(build_download_buttons(settings))
        POST_CACHE.pop(token, None)
    except Exception as e: print(f"Use Error: {e}")
    finally: raise StopPropagation

@Client.on_callback_query(cb_starts("mvcancel|"), group=-999)
async def cancel_cb(client, query):
    try:
        _, token = query.data.split("|")
        POST_CACHE.pop(token, None)
        await query.answer("Cancelled")
        await query.message.delete()
    except: pass
    finally: raise StopPropagation

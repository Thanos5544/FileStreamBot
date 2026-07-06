import os
import io
import re
import uuid
import time
import asyncio
import aiohttp
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)


# =========== CONFIG ===========
TMDB_API = os.getenv("TMDB_API", "YOUR_TMDB_API_KEY_HERE")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

DEFAULT_BRANDING = "@Patrick_Botz"
DEFAULT_CHANNEL = "@NOVA_FLIX"
DEFAULT_CAPTION = """<b>{title} ({year})</b>

➡ <b>Audio:</b> <code>Hindi</code>
➡ <b>Quality:</b> <code>480p, 720p, 1080p</code>
➡ <b>Genres:</b> <code>{genres}</code>"""

DEFAULT_BUTTON_TEXT = "🔽 Download"
DEFAULT_BUTTON_URL = "https://t.me/Patrick_Botz"

# Colors with RGB
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
CACHE_TIME = 1800
USER_SETTINGS = {}


def cb_starts(prefix: str):
    return filters.create(
        lambda _, __, query: bool(query.data and query.data.startswith(prefix))
    )


def cleanup_cache():
    now = time.time()
    for token, data in list(POST_CACHE.items()):
        if now - data.get("time", now) > CACHE_TIME:
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
        
        url = f"{TMDB_BASE}/search/multi"
        
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            results = data.get("results", [])
            
            filtered = [
                r for r in results 
                if r.get("media_type") in ["movie", "tv"]
            ]
            
            return filtered


async def get_movie_details(media_id, media_type):
    async with aiohttp.ClientSession() as session:
        params = {"api_key": TMDB_API, "append_to_response": "credits"}
        url = f"{TMDB_BASE}/{media_type}/{media_id}"
        
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def get_movie_images(media_id, media_type):
    async with aiohttp.ClientSession() as session:
        params = {
            "api_key": TMDB_API,
            "include_image_language": "en,null,hi",
        }
        url = f"{TMDB_BASE}/{media_type}/{media_id}/images"
        
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()


def get_font(size, bold=False):
    """Get font with fallback"""
    fonts_to_try = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    for font_path in fonts_to_try:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    
    return ImageFont.load_default()


def create_gradient_overlay(size, color, direction="left"):
    """Create gradient overlay"""
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    width, height = size
    
    if direction == "left":
        for x in range(width):
            alpha = int(255 * (1 - x / (width * 0.7)))
            alpha = max(0, min(255, alpha))
            draw.line(
                [(x, 0), (x, height)],
                fill=(color[0], color[1], color[2], alpha)
            )
    elif direction == "bottom":
        for y in range(height):
            alpha = int(255 * (y / height))
            alpha = max(0, min(255, alpha))
            draw.line(
                [(0, y), (width, y)],
                fill=(0, 0, 0, alpha)
            )
    
    return gradient


def truncate_text(text, max_length):
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


async def create_postify_template(image_url, movie_data, color_name=None, channel=None, branding=None):
    """Create Postify-style poster with all details"""
    
    # Download image
    img_bytes = await download_image(image_url)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    
    # Resize to landscape 1280x720
    target_size = (1280, 720)
    
    # Resize maintaining aspect ratio and crop
    img_ratio = img.size[0] / img.size[1]
    target_ratio = target_size[0] / target_size[1]
    
    if img_ratio > target_ratio:
        new_height = target_size[1]
        new_width = int(new_height * img_ratio)
    else:
        new_width = target_size[0]
        new_height = int(new_width / img_ratio)
    
    img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Crop to center
    left = (new_width - target_size[0]) // 2
    top = (new_height - target_size[1]) // 2
    img = img.crop((left, top, left + target_size[0], top + target_size[1]))
    
    # Apply color overlay if selected
    if color_name and color_name in COLORS:
        color = COLORS[color_name]
        color_overlay = Image.new("RGBA", target_size, (color[0], color[1], color[2], 100))
        img = Image.alpha_composite(img, color_overlay)
    
    # Add dark gradient from left (for text readability)
    left_gradient = create_gradient_overlay(target_size, (0, 0, 0), "left")
    img = Image.alpha_composite(img, left_gradient)
    
    # Add bottom gradient
    bottom_gradient = create_gradient_overlay(target_size, (0, 0, 0), "bottom")
    img = Image.alpha_composite(img, bottom_gradient)
    
    # Create drawing layer
    draw = ImageDraw.Draw(img)
    
    # Get movie data
    title = movie_data.get("title") or movie_data.get("name") or "Unknown"
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres = movie_data.get("genres", [])
    if genres and isinstance(genres[0], dict):
        genre_names = [g.get("name", "") for g in genres[:2]]
    else:
        genre_names = genres[:2] if genres else []
    genres_str = " & ".join(genre_names).upper() if genre_names else "MOVIE"
    
    runtime = movie_data.get("runtime") or 0
    if not runtime:
        # For TV series
        episode_time = movie_data.get("episode_run_time", [])
        runtime = episode_time[0] if episode_time else 0
    
    duration = f"{runtime} MIN" if runtime else ""
    
    overview = movie_data.get("overview", "")
    rating = movie_data.get("vote_average", 0)
    
    # Get director/creator
    credits = movie_data.get("credits", {})
    crew = credits.get("crew", [])
    director = ""
    for person in crew:
        if person.get("job") in ["Director", "Series Director"]:
            director = person.get("name", "").upper()
            break
    if not director:
        creators = movie_data.get("created_by", [])
        if creators:
            director = creators[0].get("name", "").upper()
    
    # === DRAW ELEMENTS ===
    
    # 1. Channel branding top-left
    if channel:
        channel_font = get_font(22, bold=True)
        # Small icon-like box
        draw.rectangle([(30, 30), (60, 55)], fill=(255, 255, 255, 30))
        draw.text((70, 32), channel, font=channel_font, fill=(255, 255, 255, 255))
    
    # 2. FILMED BY (Director)
    if director:
        filmed_by_font = get_font(16, bold=True)
        director_font = get_font(16, bold=True)
        
        # Get color for director name (use selected color or default green)
        if color_name and color_name in COLORS:
            dir_color = COLORS[color_name]
        else:
            dir_color = (46, 204, 113)  # Default green
        
        draw.text((30, 200), "FILMED BY", font=filmed_by_font, fill=(255, 255, 255, 200))
        
        # Calculate position for director name
        filmed_bbox = draw.textbbox((0, 0), "FILMED BY", font=filmed_by_font)
        filmed_width = filmed_bbox[2] - filmed_bbox[0]
        
        draw.text((30 + filmed_width + 10, 200), director[:30], font=director_font, fill=dir_color)
    
    # 3. BIG TITLE
    # Adjust font size based on title length
    title_upper = title.upper()
    if len(title_upper) > 20:
        title_size = 55
    elif len(title_upper) > 15:
        title_size = 70
    else:
        title_size = 85
    
    title_font = get_font(title_size, bold=True)
    draw.text((30, 240), title_upper, font=title_font, fill=(255, 255, 255, 255))
    
    # 4. Colored underline below title
    if color_name and color_name in COLORS:
        line_color = COLORS[color_name]
    else:
        line_color = (46, 204, 113)  # Green default
    
    title_bbox = draw.textbbox((30, 240), title_upper, font=title_font)
    line_width = min(title_bbox[2] - title_bbox[0], 200)
    line_y = title_bbox[3] + 10
    draw.rectangle(
        [(30, line_y), (30 + line_width, line_y + 4)],
        fill=line_color
    )
    
    # 5. Year • Genre • Duration
    info_font = get_font(20, bold=True)
    info_text = f"{year}"
    if genres_str:
        info_text += f"  •  {genres_str}"
    if duration:
        info_text += f"  •  {duration}"
    
    info_y = line_y + 25
    draw.text((30, info_y), info_text, font=info_font, fill=(220, 220, 220, 255))
    
    # 6. Story/Overview
    if overview:
        story_font = get_font(16)
        
        # Wrap text
        max_chars_per_line = 65
        words = overview.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars_per_line:
                current_line += (" " if current_line else "") + word
            else:
                lines.append(current_line)
                current_line = word
                if len(lines) >= 2:  # Max 2 lines
                    break
        
        if current_line and len(lines) < 2:
            lines.append(current_line)
        
        # Truncate last line if needed
        if len(lines) == 2 and len(overview) > 130:
            lines[1] = lines[1][:60] + "..."
        
        story_y = info_y + 40
        for line in lines:
            draw.text((30, story_y), line, font=story_font, fill=(200, 200, 200, 220))
            story_y += 22
    
    # 7. WATCH NOW Button
    button_y = target_size[1] - 120
    button_width = 200
    button_height = 55
    
    # Button background (colored)
    if color_name and color_name in COLORS:
        btn_color = COLORS[color_name]
    else:
        btn_color = (231, 76, 60)  # Red default like Netflix
    
    # Round rectangle
    draw.rounded_rectangle(
        [(30, button_y), (30 + button_width, button_y + button_height)],
        radius=8,
        fill=btn_color
    )
    
    # Button text
    btn_font = get_font(20, bold=True)
    btn_text = "▶ WATCH NOW"
    btn_bbox = draw.textbbox((0, 0), btn_text, font=btn_font)
    btn_text_width = btn_bbox[2] - btn_bbox[0]
    btn_text_x = 30 + (button_width - btn_text_width) // 2
    btn_text_y = button_y + (button_height - (btn_bbox[3] - btn_bbox[1])) // 2 - 5
    
    draw.text((btn_text_x, btn_text_y), btn_text, font=btn_font, fill=(255, 255, 255, 255))
    
    # 8. IMDB Rating Badge
    imdb_x = 30 + button_width + 15
    imdb_width = 130
    
    # IMDB badge background (dark)
    draw.rounded_rectangle(
        [(imdb_x, button_y), (imdb_x + imdb_width, button_y + button_height)],
        radius=8,
        fill=(20, 20, 20, 220),
        outline=(255, 200, 0, 255),
        width=1
    )
    
    # Star icon
    star_font = get_font(24, bold=True)
    draw.text((imdb_x + 15, button_y + 12), "✦", font=star_font, fill=(255, 200, 0, 255))
    
    # Rating text
    rating_font = get_font(18, bold=True)
    rating_text = f"{rating:.1f} IMDb" if rating else "N/A IMDb"
    draw.text((imdb_x + 45, button_y + 18), rating_text, font=rating_font, fill=(255, 255, 255, 255))
    
    # 9. Watermark bottom center
    if branding:
        wm_font = get_font(20, bold=True)
        wm_bbox = draw.textbbox((0, 0), branding, font=wm_font)
        wm_width = wm_bbox[2] - wm_bbox[0]
        wm_x = (target_size[0] - wm_width) // 2
        wm_y = target_size[1] - 40
        
        # Shadow
        draw.text((wm_x + 2, wm_y + 2), branding, font=wm_font, fill=(0, 0, 0, 200))
        # Main
        draw.text((wm_x, wm_y), branding, font=wm_font, fill=(255, 255, 255, 200))
    
    # Convert to RGB and save
    final = img.convert("RGB")
    output = io.BytesIO()
    final.save(output, format="JPEG", quality=95)
    output.seek(0)
    
    return output


def format_caption(template, movie_data):
    """Format caption with movie variables"""
    title = movie_data.get("title") or movie_data.get("name") or "Unknown"
    
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres = movie_data.get("genres", [])
    if isinstance(genres, list) and genres:
        if isinstance(genres[0], dict):
            genre_names = [g.get("name", "") for g in genres]
        else:
            genre_names = genres
        genres_str = " • ".join(genre_names)
    else:
        genres_str = "N/A"
    
    overview = movie_data.get("overview", "")
    rating = movie_data.get("vote_average", 0)
    
    caption = template.format(
        title=title,
        year=year,
        genres=genres_str,
        overview=overview[:200] + "..." if len(overview) > 200 else overview,
        rating=f"{rating:.1f}" if rating else "N/A",
        audio="Hindi & English",
        quality="480p, 720p, 1080p",
    )
    
    return caption


def build_color_buttons(token, image_index=0, total_images=1):
    buttons = []
    
    if total_images > 1:
        nav = [
            InlineKeyboardButton("⬅️ PREV", callback_data=f"postnav|{token}|prev"),
            InlineKeyboardButton(f"{image_index + 1}/{total_images}", callback_data=f"postnav|{token}|info"),
            InlineKeyboardButton("NEXT ➡️", callback_data=f"postnav|{token}|next"),
        ]
        buttons.append(nav)
    
    color_row1 = [
        InlineKeyboardButton("🔴", callback_data=f"postcolor|{token}|red"),
        InlineKeyboardButton("🟠", callback_data=f"postcolor|{token}|orange"),
        InlineKeyboardButton("🟡", callback_data=f"postcolor|{token}|yellow"),
        InlineKeyboardButton("🟢", callback_data=f"postcolor|{token}|green"),
    ]
    buttons.append(color_row1)
    
    color_row2 = [
        InlineKeyboardButton("🔵", callback_data=f"postcolor|{token}|blue"),
        InlineKeyboardButton("🟣", callback_data=f"postcolor|{token}|purple"),
        InlineKeyboardButton("⚫", callback_data=f"postcolor|{token}|black"),
        InlineKeyboardButton("⚪", callback_data=f"postcolor|{token}|white"),
    ]
    buttons.append(color_row2)
    
    buttons.append([
        InlineKeyboardButton("✅ USE NORMAL", callback_data=f"postuse|{token}|normal")
    ])
    
    buttons.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"postcancel|{token}")
    ])
    
    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["movie", "post", "tv"]))
async def movie_post_handler(client, message):
    cleanup_cache()
    
    if len(message.command) < 2:
        return await message.reply_text(
            "🎬 **Movie Post Generator**\n\n"
            "**Usage:**\n"
            "`/movie the witcher 2019`\n"
            "`/movie pathaan 2023`\n"
            "`/tv breaking bad`"
        )
    
    query_text = " ".join(message.command[1:])
    
    year_match = re.search(r"\b(19|20)\d{2}\b", query_text)
    year = year_match.group() if year_match else None
    
    if year:
        query = query_text.replace(year, "").strip()
    else:
        query = query_text
    
    msg = await message.reply_text(
        f"🔍 **Searching:** `{query_text}`\n\n"
        f"⏳ Please wait..."
    )
    
    try:
        results = await search_movie(query, year)
        
        if not results:
            return await msg.edit_text("❌ **Movie/Series not found**")
        
        movie = results[0]
        
        if year:
            for r in results:
                date = r.get("release_date") or r.get("first_air_date", "")
                if date.startswith(year):
                    movie = r
                    break
        
        media_type = movie.get("media_type", "movie")
        movie_id = movie["id"]
        
        details = await get_movie_details(movie_id, media_type)
        images = await get_movie_images(movie_id, media_type)
        
        backdrops = images.get("backdrops", [])
        image_urls = []
        
        if details.get("backdrop_path"):
            image_urls.append(TMDB_IMG + details["backdrop_path"])
        
        for bd in backdrops[:20]:
            url = TMDB_IMG + bd["file_path"]
            if url not in image_urls:
                image_urls.append(url)
        
        if not image_urls:
            return await msg.edit_text("❌ **No images found**")
        
        token = uuid.uuid4().hex[:10]
        POST_CACHE[token] = {
            "images": image_urls,
            "current_index": 0,
            "movie_data": details,
            "selected_color": None,
            "user_id": message.from_user.id if message.from_user else 0,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "time": time.time()
        }
        
        settings = get_user_settings(message.from_user.id)
        
        # Create Postify-style poster
        poster = await create_postify_template(
            image_urls[0],
            details,
            color_name=None,
            channel=settings.get("channel", DEFAULT_CHANNEL),
            branding=settings["branding"]
        )
        
        caption = format_caption(settings["caption"], details)
        
        await msg.delete()
        
        await client.send_photo(
            chat_id=message.chat.id,
            photo=poster,
            caption=caption,
            reply_markup=build_color_buttons(token, 0, len(image_urls)),
            reply_to_message_id=message.id,
            parse_mode=ParseMode.HTML
        )
        
        except Exception as e:
        await msg.edit_text(
            f"❌ **Error**\n\n`{str(e)[:500]}`"
        )


@Client.on_callback_query(cb_starts("postnav|"), group=-999)
async def post_nav_callback(client, query):
    try:
        cleanup_cache()
        
        try:
            _, token, action = query.data.split("|")
        except Exception:
            await query.answer("Invalid", show_alert=True)
            return
        
        data = POST_CACHE.get(token)
        if not data:
            await query.answer("Expired. /movie dobara try karo.", show_alert=True)
            return
        
        if query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai bhai", show_alert=True)
            return
        
        if action == "info":
            await query.answer(f"Image {data['current_index'] + 1} of {len(data['images'])}")
            return
        
        current = data["current_index"]
        total = len(data["images"])
        
        if action == "next":
            new_index = (current + 1) % total
        elif action == "prev":
            new_index = (current - 1) % total
        else:
            return
        
        data["current_index"] = new_index
        
        await query.answer(f"Loading image {new_index + 1}...")
        
        settings = get_user_settings(query.from_user.id)
        
        poster = await create_postify_template(
            data["images"][new_index],
            data["movie_data"],
            color_name=data.get("selected_color"),
            channel=settings.get("channel", DEFAULT_CHANNEL),
            branding=settings["branding"]
        )
        
        caption = format_caption(settings["caption"], data["movie_data"])
        
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=poster,
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=build_color_buttons(token, new_index, total)
        )
    
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postcolor|"), group=-999)
async def post_color_callback(client, query):
    try:
        cleanup_cache()
        
        try:
            _, token, color = query.data.split("|")
        except Exception:
            await query.answer("Invalid", show_alert=True)
            return
        
        data = POST_CACHE.get(token)
        if not data:
            await query.answer("Expired", show_alert=True)
            return
        
        if query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai", show_alert=True)
            return
        
        await query.answer(f"Applied {color}")
        
        data["selected_color"] = color
        
        settings = get_user_settings(query.from_user.id)
        
        poster = await create_postify_template(
            data["images"][data["current_index"]],
            data["movie_data"],
            color_name=color,
            channel=settings.get("channel", DEFAULT_CHANNEL),
            branding=settings["branding"]
        )
        
        caption = format_caption(settings["caption"], data["movie_data"])
        
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=poster,
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=build_color_buttons(
                token, data["current_index"], len(data["images"])
            )
        )
    
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postuse|"), group=-999)
async def post_use_callback(client, query):
    try:
        try:
            _, token, action = query.data.split("|")
        except Exception:
            await query.answer("Invalid", show_alert=True)
            return
        
        data = POST_CACHE.get(token)
        if not data:
            await query.answer("Expired", show_alert=True)
            return
        
        if query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai", show_alert=True)
            return
        
        await query.answer("✅ Post finalized!")
        
        settings = get_user_settings(query.from_user.id)
        
        download_button = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                settings["button_text"],
                url=settings["button_url"]
            )
        ]])
        
        await query.message.edit_reply_markup(download_button)
        
        POST_CACHE.pop(token, None)
    
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("postcancel|"), group=-999)
async def post_cancel_callback(client, query):
    try:
        try:
            _, token = query.data.split("|")
        except Exception:
            await query.answer("Invalid", show_alert=True)
            return
        
        data = POST_CACHE.get(token)
        if data and query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai", show_alert=True)
            return
        
        POST_CACHE.pop(token, None)
        
        await query.answer("Cancelled")
        await query.message.delete()
    
    finally:
        raise StopPropagation

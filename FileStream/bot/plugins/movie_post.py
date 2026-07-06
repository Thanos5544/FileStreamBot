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
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


# =========== CONFIG ===========
TMDB_API = os.getenv("TMDB_API", "YOUR_TMDB_API_KEY_HERE")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

# Default settings
DEFAULT_BRANDING = "@Patrick_Botz"
DEFAULT_CAPTION = """<b>{title} ({year})</b>

➡ <b>Audio:</b> <code>Hindi</code>
➡ <b>Quality:</b> <code>480p, 720p, 1080p</code>
➡ <b>Genres:</b> <code>{genres}</code>"""

DEFAULT_BUTTON_TEXT = "🔽 Download"
DEFAULT_BUTTON_URL = "https://t.me/Patrick_Botz"

# Colors for overlay
COLORS = {
    "red": (231, 76, 60),
    "orange": (230, 126, 34),
    "yellow": (241, 196, 15),
    "green": (46, 204, 113),
    "blue": (52, 152, 219),
    "purple": (155, 89, 182),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
}

# Cache
POST_CACHE = {}
CACHE_TIME = 1800

# User settings (in-memory - can be moved to DB)
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
    """Get user settings or defaults"""
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {
            "branding": DEFAULT_BRANDING,
            "caption": DEFAULT_CAPTION,
            "button_text": DEFAULT_BUTTON_TEXT,
            "button_url": DEFAULT_BUTTON_URL,
            "color": None,  # No color by default
        }
    return USER_SETTINGS[user_id]


async def search_movie(query, year=None):
    """Search movie on TMDB"""
    async with aiohttp.ClientSession() as session:
        params = {
            "api_key": TMDB_API,
            "query": query,
        }
        if year:
            params["year"] = year
        
        url = f"{TMDB_BASE}/search/multi"
        
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            results = data.get("results", [])
            
            # Filter movies and TV
            filtered = [
                r for r in results 
                if r.get("media_type") in ["movie", "tv"]
            ]
            
            return filtered


async def get_movie_details(media_id, media_type):
    """Get detailed info"""
    async with aiohttp.ClientSession() as session:
        params = {"api_key": TMDB_API}
        url = f"{TMDB_BASE}/{media_type}/{media_id}"
        
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def get_movie_images(media_id, media_type):
    """Get all images"""
    async with aiohttp.ClientSession() as session:
        params = {
            "api_key": TMDB_API,
            "include_image_language": "en,null,hi",
        }
        url = f"{TMDB_BASE}/{media_type}/{media_id}/images"
        
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def download_image(url):
    """Download image bytes"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()


def apply_color_overlay(image, color_name, opacity=0.4):
    """Apply color overlay to image"""
    if not color_name or color_name not in COLORS:
        return image
    
    color = COLORS[color_name]
    
    # Create overlay
    overlay = Image.new("RGB", image.size, color)
    
    # Blend
    result = Image.blend(image.convert("RGB"), overlay, opacity)
    
    return result


def add_watermark(image, text, position="bottom"):
    """Add watermark text to image"""
    img = image.convert("RGBA")
    txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    
    draw = ImageDraw.Draw(txt_layer)
    
    # Font size based on image width
    font_size = max(20, img.size[0] // 40)
    
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            font_size
        )
    except:
        font = ImageFont.load_default()
    
    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position
    if position == "bottom":
        x = (img.size[0] - text_width) // 2
        y = img.size[1] - text_height - 30
    elif position == "top":
        x = (img.size[0] - text_width) // 2
        y = 20
    else:
        x = (img.size[0] - text_width) // 2
        y = (img.size[1] - text_height) // 2
    
    # Draw shadow
    shadow_offset = 3
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill=(0, 0, 0, 200)
    )
    
    # Draw main text
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(255, 255, 255, 255)
    )
    
    # Combine
    combined = Image.alpha_composite(img, txt_layer)
    return combined.convert("RGB")


async def create_poster(image_url, color=None, branding=None):
    """Create final poster with overlay and branding"""
    # Download image
    img_bytes = await download_image(image_url)
    img = Image.open(io.BytesIO(img_bytes))
    
    # Resize if needed
    if img.size[0] > 1920:
        ratio = 1920 / img.size[0]
        new_size = (1920, int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Apply color overlay
    if color:
        img = apply_color_overlay(img, color)
    
    # Add watermark/branding
    if branding:
        img = add_watermark(img, branding, position="bottom")
    
    # Save to bytes
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=95)
    output.seek(0)
    
    return output


def format_caption(template, movie_data):
    """Format caption with movie variables"""
    # Get title
    title = (
        movie_data.get("title") or 
        movie_data.get("name") or 
        "Unknown"
    )
    
    # Get year
    date = (
        movie_data.get("release_date") or 
        movie_data.get("first_air_date") or 
        ""
    )
    year = date[:4] if date else "N/A"
    
    # Get genres
    genres = movie_data.get("genres", [])
    if isinstance(genres, list) and genres:
        if isinstance(genres[0], dict):
            genre_names = [g.get("name", "") for g in genres]
        else:
            genre_names = genres
        genres_str = " • ".join(genre_names)
    else:
        genres_str = "N/A"
    
    # Get overview
    overview = movie_data.get("overview", "")
    
    # Get rating
    rating = movie_data.get("vote_average", 0)
    
    # Replace variables
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
    """Build inline keyboard with color options"""
    buttons = []
    
    # Navigation
    if total_images > 1:
        nav = [
            InlineKeyboardButton(
                "⬅️ PREV",
                callback_data=f"postnav|{token}|prev"
            ),
            InlineKeyboardButton(
                f"{image_index + 1}/{total_images}",
                callback_data=f"postnav|{token}|info"
            ),
            InlineKeyboardButton(
                "NEXT ➡️",
                callback_data=f"postnav|{token}|next"
            ),
        ]
        buttons.append(nav)
    
    # Color options - Row 1
    color_row1 = [
        InlineKeyboardButton("🔴", callback_data=f"postcolor|{token}|red"),
        InlineKeyboardButton("🟠", callback_data=f"postcolor|{token}|orange"),
        InlineKeyboardButton("🟡", callback_data=f"postcolor|{token}|yellow"),
        InlineKeyboardButton("🟢", callback_data=f"postcolor|{token}|green"),
    ]
    buttons.append(color_row1)
    
    # Color options - Row 2
    color_row2 = [
        InlineKeyboardButton("🔵", callback_data=f"postcolor|{token}|blue"),
        InlineKeyboardButton("🟣", callback_data=f"postcolor|{token}|purple"),
        InlineKeyboardButton("⚫", callback_data=f"postcolor|{token}|black"),
        InlineKeyboardButton("⚪", callback_data=f"postcolor|{token}|white"),
    ]
    buttons.append(color_row2)
    
    # Action buttons
    buttons.append([
        InlineKeyboardButton(
            "✅ USE NORMAL",
            callback_data=f"postuse|{token}|normal"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data=f"postcancel|{token}"
        )
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
    
    # Extract year if present
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
        # Search
        results = await search_movie(query, year)
        
        if not results:
            return await msg.edit_text("❌ **Movie/Series not found**")
        
        # Take first result
        movie = results[0]
        
        # If year specified, try to match
        if year:
            for r in results:
                date = r.get("release_date") or r.get("first_air_date", "")
                if date.startswith(year):
                    movie = r
                    break
        
        media_type = movie.get("media_type", "movie")
        movie_id = movie["id"]
        
        # Get full details
        details = await get_movie_details(movie_id, media_type)
        
        # Get all images
        images = await get_movie_images(movie_id, media_type)
        
        # Collect all backdrops
        backdrops = images.get("backdrops", [])
        image_urls = []
        
        # Add main backdrop
        if details.get("backdrop_path"):
            image_urls.append(TMDB_IMG + details["backdrop_path"])
        
        # Add all backdrops
        for bd in backdrops[:20]:  # Max 20 images
            url = TMDB_IMG + bd["file_path"]
            if url not in image_urls:
                image_urls.append(url)
        
        if not image_urls:
            return await msg.edit_text("❌ **No images found**")
        
        # Create token
        token = uuid.uuid4().hex[:10]
        POST_CACHE[token] = {
            "images": image_urls,
            "current_index": 0,
            "movie_data": details,
            "user_id": message.from_user.id if message.from_user else 0,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "time": time.time()
        }
        
        # Get user settings
        settings = get_user_settings(message.from_user.id)
        
        # Create first poster
        poster = await create_poster(
            image_urls[0],
            color=None,
            branding=settings["branding"]
        )
        
        # Format caption
        caption = format_caption(settings["caption"], details)
        
        # Send image with buttons
        await msg.delete()
        
        await client.send_photo(
            chat_id=message.chat.id,
            photo=poster,
            caption=caption,
            reply_markup=build_color_buttons(token, 0, len(image_urls)),
            reply_to_message_id=message.id
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
            await query.answer("Expired. Dobara /movie try karo.", show_alert=True)
            return
        
        if query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai bhai", show_alert=True)
            return
        
        if action == "info":
            await query.answer(
                f"Image {data['current_index'] + 1} of {len(data['images'])}"
            )
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
        
        # Get selected color from cache
        selected_color = data.get("selected_color")
        
        # Create new poster
        poster = await create_poster(
            data["images"][new_index],
            color=selected_color,
            branding=settings["branding"]
        )
        
        caption = format_caption(settings["caption"], data["movie_data"])
        
        # Update message
        from pyrogram.types import InputMediaPhoto
        
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=poster,
                caption=caption
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
        
        await query.answer(f"Applied {color} filter")
        
        # Save selected color
        data["selected_color"] = color
        
        settings = get_user_settings(query.from_user.id)
        
        # Create poster with color
        poster = await create_poster(
            data["images"][data["current_index"]],
            color=color,
            branding=settings["branding"]
        )
        
        caption = format_caption(settings["caption"], data["movie_data"])
        
        from pyrogram.types import InputMediaPhoto
        
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=poster,
                caption=caption
            ),
            reply_markup=build_color_buttons(
                token,
                data["current_index"],
                len(data["images"])
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
        
        # Add download button
        settings = get_user_settings(query.from_user.id)
        
        download_button = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                settings["button_text"],
                url=settings["button_url"]
            )
        ]])
        
        # Update with final buttons
        await query.message.edit_reply_markup(download_button)
        
        # Cleanup
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

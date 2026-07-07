import os
import re
import uuid
import time
import aiohttp

from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)


TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

DEFAULT_BRANDING = "@Patrick_Botz"
DEFAULT_CHANNEL = "@Patrick_Botz"
DEFAULT_CAPTION = """<b>{title} ({year})</b>

➡ <b>Audio:</b> <code>Hindi</code>
➡ <b>Quality:</b> <code>480p, 720p, 1080p</code>
➡ <b>Genres:</b> <code>{genres}</code>"""

DEFAULT_BUTTON_TEXT = "🔽 Download"
DEFAULT_BUTTON_URL = "https://t.me/Patrick_Botz"

POST_CACHE = {}
USER_SETTINGS = {}


def cb_starts(prefix):
    return filters.create(
        lambda _, __, query: bool(query.data and query.data.startswith(prefix))
    )


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
        params = {"api_key": TMDB_API}
        async with session.get(f"{TMDB_BASE}/{media_type}/{media_id}", params=params) as resp:
            return await resp.json()


async def get_movie_images(media_id, media_type):
    async with aiohttp.ClientSession() as session:
        params = {"api_key": TMDB_API, "include_image_language": "en,null,hi"}
        async with session.get(f"{TMDB_BASE}/{media_type}/{media_id}/images", params=params) as resp:
            return await resp.json()


def format_caption(movie_data, settings):
    title = movie_data.get("title") or movie_data.get("name") or "Unknown"
    date = movie_data.get("release_date") or movie_data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"
    
    genres = movie_data.get("genres", [])
    if genres and isinstance(genres[0], dict):
        gnames = [g.get("name", "") for g in genres]
    else:
        gnames = genres if genres else []
    genres_str = " • ".join(gnames) if gnames else "N/A"
    
    rating = movie_data.get("vote_average", 0)
    overview = movie_data.get("overview", "")
    
    template = settings.get("caption", DEFAULT_CAPTION)
    
    try:
        caption = template.format(
            title=title,
            year=year,
            genres=genres_str,
            audio="Hindi & English",
            quality="480p, 720p, 1080p",
            rating=f"{rating:.1f}" if rating else "N/A",
            overview=overview[:200] + "..." if len(overview) > 200 else overview,
        )
    except:
        caption = f"<b>{title} ({year})</b>\n\n➡ <b>Genres:</b> <code>{genres_str}</code>"
    
    return caption


def build_color_buttons(token, idx=0, total=1):
    """Build buttons with color options and navigation"""
    buttons = []
    
    if total > 1:
        buttons.append([
            InlineKeyboardButton("⬅️ PREV", callback_data=f"mvnav|{token}|prev"),
            InlineKeyboardButton(f"{idx + 1}/{total}", callback_data=f"mvnav|{token}|info"),
            InlineKeyboardButton("NEXT ➡️", callback_data=f"mvnav|{token}|next"),
        ])
    
    color_row1 = [
        InlineKeyboardButton("🔴", callback_data=f"mvcolor|{token}|red"),
        InlineKeyboardButton("🟠", callback_data=f"mvcolor|{token}|orange"),
        InlineKeyboardButton("🟡", callback_data=f"mvcolor|{token}|yellow"),
        InlineKeyboardButton("🟢", callback_data=f"mvcolor|{token}|green"),
    ]
    buttons.append(color_row1)
    
    color_row2 = [
        InlineKeyboardButton("🔵", callback_data=f"mvcolor|{token}|blue"),
        InlineKeyboardButton("🟣", callback_data=f"mvcolor|{token}|purple"),
        InlineKeyboardButton("⚫", callback_data=f"mvcolor|{token}|black"),
        InlineKeyboardButton("⚪", callback_data=f"mvcolor|{token}|white"),
    ]
    buttons.append(color_row2)
    
    buttons.append([
        InlineKeyboardButton("✅ USE NORMAL", callback_data=f"mvuse|{token}|normal")
    ])
    
    buttons.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"mvcancel|{token}")
    ])
    
    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["movie", "post", "tv"]))
async def movie_handler(client, message):
    cleanup_cache()
    
    if len(message.command) < 2:
        return await message.reply_text(
            "🎬 <b>Movie Post Generator</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/movie the witcher 2019</code>\n"
            "<code>/movie pathaan 2023</code>\n"
            "<code>/tv breaking bad</code>\n\n"
            "<b>Settings:</b>\n"
            "<code>/postsettings</code>"
        )
    
    query_text = " ".join(message.command[1:])
    ym = re.search(r"\b(19|20)\d{2}\b", query_text)
    year = ym.group() if ym else None
    query = query_text.replace(year, "").strip() if year else query_text
    
    msg = await message.reply_text(f"🔍 <b>Searching:</b> <code>{query_text}</code>")
    
    try:
        results = await search_movie(query, year)
        
        if not results:
            return await msg.edit_text("❌ <b>Movie/Series not found</b>")
        
        movie = results[0]
        if year:
            for r in results:
                d = r.get("release_date") or r.get("first_air_date", "")
                if d.startswith(year):
                    movie = r
                    break
        
        media_type = movie.get("media_type", "movie")
        details = await get_movie_details(movie["id"], media_type)
        images = await get_movie_images(movie["id"], media_type)
        
        image_urls = []
        if details.get("backdrop_path"):
            image_urls.append(TMDB_IMG + details["backdrop_path"])
        for bd in images.get("backdrops", [])[:20]:
            url = TMDB_IMG + bd["file_path"]
            if url not in image_urls:
                image_urls.append(url)
        
        if not image_urls:
            return await msg.edit_text("❌ <b>No images found</b>")
        
        token = uuid.uuid4().hex[:10]
        POST_CACHE[token] = {
            "images": image_urls,
            "current_index": 0,
            "movie_data": details,
            "selected_color": None,
            "user_id": message.from_user.id,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "time": time.time()
        }
        
        settings = get_user_settings(message.from_user.id)
        caption = format_caption(details, settings)
        
        await msg.delete()
        
        await client.send_photo(
            chat_id=message.chat.id,
            photo=image_urls[0],
            caption=caption,
            reply_markup=build_color_buttons(token, 0, len(image_urls)),
            reply_to_message_id=message.id,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        await msg.edit_text(f"❌ <b>Error</b>\n\n<code>{str(e)[:400]}</code>")


@Client.on_callback_query(cb_starts("mvnav|"), group=-999)
async def movie_nav_callback(client, query):
    try:
        _, token, action = query.data.split("|")
        
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired! Try /movie again", show_alert=True)
        
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        
        if action == "info":
            return await query.answer(f"{data['current_index'] + 1}/{len(data['images'])}")
        
        total = len(data["images"])
        
        if action == "next":
            data["current_index"] = (data["current_index"] + 1) % total
        else:
            data["current_index"] = (data["current_index"] - 1) % total
        
        await query.answer(f"Loading image {data['current_index'] + 1}")
        
        settings = get_user_settings(query.from_user.id)
        caption = format_caption(data["movie_data"], settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=data["images"][data["current_index"]],
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=build_color_buttons(token, data["current_index"], total)
        )
    
    except Exception as e:
        print(f"Nav error: {e}")
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("mvcolor|"), group=-999)
async def movie_color_callback(client, query):
    try:
        _, token, color = query.data.split("|")
        
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired!", show_alert=True)
        
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        
        await query.answer(f"Applied {color} color")
        
        data["selected_color"] = color
        
        settings = get_user_settings(query.from_user.id)
        caption = format_caption(data["movie_data"], settings)
        
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=data["images"][data["current_index"]],
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=build_color_buttons(
                token,
                data["current_index"],
                len(data["images"])
            )
        )
    
    except Exception as e:
        print(f"Color error: {e}")
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("mvuse|"), group=-999)
async def movie_use_callback(client, query):
    try:
        try:
            _, token, action = query.data.split("|")
        except:
            _, token = query.data.split("|")
            action = "normal"
        
        data = POST_CACHE.get(token)
        if not data:
            return await query.answer("Expired!", show_alert=True)
        
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        
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
    
    except Exception as e:
        print(f"Use error: {e}")
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("mvcancel|"), group=-999)
async def movie_cancel_callback(client, query):
    try:
        _, token = query.data.split("|")
        
        data = POST_CACHE.get(token)
        if data and query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)
        
        POST_CACHE.pop(token, None)
        await query.answer("Cancelled")
        await query.message.delete()
    
    except Exception as e:
        print(f"Cancel error: {e}")
    finally:
        raise StopPropagation

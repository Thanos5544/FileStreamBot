import os
import re
import time
import uuid
import asyncio
import aiohttp

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

IMG_CACHE = {}

CACHE_TIME = 1800  # 30 min


def cleanup_cache():
    now = time.time()
    for token, data in list(IMG_CACHE.items()):
        if now - data.get("time", now) > CACHE_TIME:
            IMG_CACHE.pop(token, None)


def tmdb_img_url(path):
    if not path:
        return None
    return TMDB_IMG + path


def image_language(img):
    return img.get("iso_639_1")


def get_title(movie):
    return (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "Unknown"
    )


def get_year(movie):
    date = movie.get("release_date") or movie.get("first_air_date")
    if date and len(date) >= 4:
        return date[:4]
    return "Unknown"


def build_category_buttons(token, categories):
    buttons = []

    if categories.get("logos"):
        buttons.append([
            InlineKeyboardButton(
                f"🔤 Logos ({len(categories['logos'])})",
                callback_data=f"imgcat|{token}|logos"
            )
        ])

    if categories.get("posters_all"):
        buttons.append([
            InlineKeyboardButton(
                f"🖼 Posters All ({len(categories['posters_all'])})",
                callback_data=f"imgcat|{token}|posters_all"
            )
        ])

    if categories.get("posters_en"):
        buttons.append([
            InlineKeyboardButton(
                f"🇬🇧 English Posters ({len(categories['posters_en'])})",
                callback_data=f"imgcat|{token}|posters_en"
            )
        ])

    if categories.get("posters_hi"):
        buttons.append([
            InlineKeyboardButton(
                f"🇮🇳 Hindi Posters ({len(categories['posters_hi'])})",
                callback_data=f"imgcat|{token}|posters_hi"
            )
        ])

    if categories.get("backdrops"):
        buttons.append([
            InlineKeyboardButton(
                f"🌄 Landscape / Backdrops ({len(categories['backdrops'])})",
                callback_data=f"imgcat|{token}|backdrops"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data=f"imgcancel|{token}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def build_count_buttons(token, category, total):
    buttons = []

    row = []
    for count in [10, 20, 30]:
        row.append(
            InlineKeyboardButton(
                f"{count}",
                callback_data=f"imgsend|{token}|{category}|{count}"
            )
        )

    buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            f"📦 All ({total})",
            callback_data=f"imgsend|{token}|{category}|all"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Back",
            callback_data=f"imgback|{token}"
        ),
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data=f"imgcancel|{token}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def search_tmdb(session, query):
    async with session.get(
        f"{TMDB_BASE}/search/multi",
        params={
            "api_key": TMDB_API,
            "query": query
        }
    ) as resp:
        return await resp.json()


async def fetch_images(session, media_type, movie_id):
    async with session.get(
        f"{TMDB_BASE}/{media_type}/{movie_id}/images",
        params={
            "api_key": TMDB_API,
            # English, Hindi aur no-language images include karega
            "include_image_language": "en,hi,null"
        }
    ) as resp:
        return await resp.json()


def select_movie(results, year=None):
    filtered = [
        x for x in results
        if x.get("media_type") in ["movie", "tv"]
    ]

    if not filtered:
        return None

    movie = filtered[0]

    if year:
        for x in filtered:
            date = x.get("release_date") or x.get("first_air_date")
            if date and date.startswith(year):
                movie = x
                break

    return movie


def make_categories(movie, data):
    posters = data.get("posters", []) or []
    backdrops = data.get("backdrops", []) or []
    logos = data.get("logos", []) or []

    categories = {
        "logos": [],
        "posters_all": [],
        "posters_en": [],
        "posters_hi": [],
        "backdrops": []
    }

    # Main poster bhi add
    if movie.get("poster_path"):
        categories["posters_all"].append(tmdb_img_url(movie["poster_path"]))

    # Main backdrop bhi add
    if movie.get("backdrop_path"):
        categories["backdrops"].append(tmdb_img_url(movie["backdrop_path"]))

    for img in posters:
        url = tmdb_img_url(img.get("file_path"))
        if not url:
            continue

        lang = image_language(img)

        categories["posters_all"].append(url)

        if lang == "en":
            categories["posters_en"].append(url)

        if lang == "hi":
            categories["posters_hi"].append(url)

    for img in backdrops:
        url = tmdb_img_url(img.get("file_path"))
        if url:
            categories["backdrops"].append(url)

    for img in logos:
        url = tmdb_img_url(img.get("file_path"))
        if url:
            categories["logos"].append(url)

    # Duplicate remove
    for key in categories:
        categories[key] = list(dict.fromkeys(categories[key]))

    return categories


async def send_images(client, chat_id, images, reply_to_message_id=None):
    for i in range(0, len(images), 10):
        chunk = images[i:i + 10]

        if len(chunk) == 1:
            await client.send_photo(
                chat_id=chat_id,
                photo=chunk[0],
                reply_to_message_id=reply_to_message_id
            )
        else:
            album = [InputMediaPhoto(media=url) for url in chunk]

            await client.send_media_group(
                chat_id=chat_id,
                media=album,
                reply_to_message_id=reply_to_message_id
            )

        await asyncio.sleep(1)


@Client.on_message(filters.command("img"))
async def img(client: Client, message: Message):
    cleanup_cache()

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n"
            "`/img movie name year`\n\n"
            "Example:\n"
            "`/img pathaan 2023`"
        )

    name = " ".join(message.command[1:]).strip()

    msg = await message.reply_text("🔎 Searching movie/images...")

    try:
        year = None
        match = re.search(r"(19|20)\d{2}", name)

        if match:
            year = match.group()
            search_name = name.replace(year, "").strip()
        else:
            search_name = name

        async with aiohttp.ClientSession() as session:
            search = await search_tmdb(session, search_name)

            results = search.get("results", [])
            movie = select_movie(results, year)

            if not movie:
                return await msg.edit_text("❌ Movie/Series not found.")

            media_type = movie.get("media_type", "movie")
            movie_id = movie["id"]

            data = await fetch_images(session, media_type, movie_id)

        categories = make_categories(movie, data)

        total_images = sum(len(v) for v in categories.values())

        if total_images == 0:
            return await msg.edit_text("❌ Is movie ke images nahi mile.")

        token = uuid.uuid4().hex[:10]

        IMG_CACHE[token] = {
            "user_id": message.from_user.id if message.from_user else 0,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "movie": movie,
            "categories": categories,
            "time": time.time()
        }

        title = get_title(movie)
        movie_year = get_year(movie)

        await msg.edit_text(
            f"🎬 **{title}** ({movie_year})\n\n"
            f"Images category select karo:",
            reply_markup=build_category_buttons(token, categories)
        )

    except Exception as e:
        print("IMG ERROR:", e)
        await msg.edit_text(
            "❌ Error aaya bro.\n\n"
            f"`{str(e)[:900]}`"
        )


@Client.on_callback_query(filters.regex(r"^imgcat\|"))
async def img_category(client: Client, query: CallbackQuery):
    cleanup_cache()

    try:
        _, token, category = query.data.split("|")
    except Exception:
        return await query.answer("Invalid button.", show_alert=True)

    data = IMG_CACHE.get(token)

    if not data:
        return await query.answer(
            "Expired ho gaya. Dobara /img command use karo.",
            show_alert=True
        )

    if query.from_user.id != data["user_id"]:
        return await query.answer(
            "Ye buttons tumhare liye nahi hain bro.",
            show_alert=True
        )

    categories = data["categories"]
    images = categories.get(category, [])

    if not images:
        return await query.answer("Is category me images nahi hain.", show_alert=True)

    category_name = {
        "logos": "Logos",
        "posters_all": "Posters All",
        "posters_en": "English Posters",
        "posters_hi": "Hindi Posters",
        "backdrops": "Landscape / Backdrops"
    }.get(category, category)

    movie = data["movie"]
    title = get_title(movie)
    movie_year = get_year(movie)

    await query.answer(category_name)

    await query.message.edit_text(
        f"🎬 **{title}** ({movie_year})\n"
        f"📁 Category: **{category_name}**\n"
        f"🖼 Available: **{len(images)}**\n\n"
        f"Kitni images bhejni hain?",
        reply_markup=build_count_buttons(token, category, len(images))
    )


@Client.on_callback_query(filters.regex(r"^imgsend\|"))
async def img_send(client: Client, query: CallbackQuery):
    cleanup_cache()

    try:
        _, token, category, count = query.data.split("|")
    except Exception:
        return await query.answer("Invalid button.", show_alert=True)

    data = IMG_CACHE.get(token)

    if not data:
        return await query.answer(
            "Expired ho gaya. Dobara /img command use karo.",
            show_alert=True
        )

    if query.from_user.id != data["user_id"]:
        return await query.answer(
            "Ye buttons tumhare liye nahi hain bro.",
            show_alert=True
        )

    images = data["categories"].get(category, [])

    if not images:
        return await query.answer("Images nahi mili.", show_alert=True)

    if count == "all":
        limit = len(images)
    else:
        limit = int(count)

    selected = images[:limit]

    category_name = {
        "logos": "Logos",
        "posters_all": "Posters All",
        "posters_en": "English Posters",
        "posters_hi": "Hindi Posters",
        "backdrops": "Landscape / Backdrops"
    }.get(category, category)

    await query.answer(f"Sending {len(selected)} images")

    await query.message.edit_text(
        f"⬆️ Uploading **{len(selected)}** {category_name} to Telegram..."
    )

    try:
        await send_images(
            client=client,
            chat_id=query.message.chat.id,
            images=selected,
            reply_to_message_id=data.get("reply_to")
        )

        await query.message.delete()
        IMG_CACHE.pop(token, None)

    except Exception as e:
        print("MEDIA ERROR:", e)
        await query.message.edit_text(
            "❌ Images send nahi hui.\n\n"
            f"`{str(e)[:900]}`"
        )


@Client.on_callback_query(filters.regex(r"^imgback\|"))
async def img_back(client: Client, query: CallbackQuery):
    cleanup_cache()

    try:
        _, token = query.data.split("|")
    except Exception:
        return await query.answer("Invalid button.", show_alert=True)

    data = IMG_CACHE.get(token)

    if not data:
        return await query.answer(
            "Expired ho gaya. Dobara /img command use karo.",
            show_alert=True
        )

    if query.from_user.id != data["user_id"]:
        return await query.answer(
            "Ye buttons tumhare liye nahi hain bro.",
            show_alert=True
        )

    movie = data["movie"]
    categories = data["categories"]

    title = get_title(movie)
    movie_year = get_year(movie)

    await query.answer("Back")

    await query.message.edit_text(
        f"🎬 **{title}** ({movie_year})\n\n"
        f"Images category select karo:",
        reply_markup=build_category_buttons(token, categories)
    )


@Client.on_callback_query(filters.regex(r"^imgcancel\|"))
async def img_cancel(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
    except Exception:
        return await query.answer("Invalid button.", show_alert=True)

    data = IMG_CACHE.get(token)

    if data and query.from_user.id != data["user_id"]:
        return await query.answer(
            "Ye buttons tumhare liye nahi hain bro.",
            show_alert=True
        )

    IMG_CACHE.pop(token, None)

    await query.answer("Cancelled")
    await query.message.edit_text("❌ Cancelled.")

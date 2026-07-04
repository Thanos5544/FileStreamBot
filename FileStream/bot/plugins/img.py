import os
import re
import time
import uuid
import asyncio
import aiohttp

from pyrogram import Client, filters, StopPropagation
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


TMDB_API = os.getenv("TMDB_API", "18303910643c603ebb9e370f2f49db56")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"

IMG_CACHE = {}
CACHE_TIME = 1800
PAGE_SIZE = 10


def cb_starts(prefix: str):
    return filters.create(
        lambda _, __, query: bool(query.data and query.data.startswith(prefix))
    )


def cleanup_cache():
    now = time.time()
    for token, data in list(IMG_CACHE.items()):
        if now - data.get("time", now) > CACHE_TIME:
            IMG_CACHE.pop(token, None)


def get_bot_token(client):
    token = (
        os.getenv("BOT_TOKEN")
        or os.getenv("TG_BOT_TOKEN")
        or os.getenv("TOKEN")
        or getattr(client, "bot_token", None)
    )

    if not token:
        raise Exception(
            "BOT_TOKEN env nahi mila. Koyeb me BOT_TOKEN add karo."
        )

    return token


def tmdb_img_url(path):
    if not path:
        return None
    return TMDB_IMG + path


def remove_duplicates(items):
    return list(dict.fromkeys(items))


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


def category_title(category):
    names = {
        "logos": "Logos",
        "posters_all": "Portrait Posters",
        "posters_en": "English Posters",
        "posters_hi": "Hindi Posters",
        "landscape": "Landscape",
        "backdrops": "Backdrops",
    }
    return names.get(category, category)


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
                f"🖼 Portrait Posters ({len(categories['posters_all'])})",
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

    if categories.get("landscape"):
        buttons.append([
            InlineKeyboardButton(
                f"🌄 Landscape ({len(categories['landscape'])})",
                callback_data=f"imgcat|{token}|landscape"
            )
        ])

    if categories.get("backdrops"):
        buttons.append([
            InlineKeyboardButton(
                f"🎞 Backdrops ({len(categories['backdrops'])})",
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


def build_page_buttons(token, category, page, total):
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    start = page * PAGE_SIZE + 1
    end = min((page + 1) * PAGE_SIZE, total)
    current_count = end - start + 1

    buttons = []

    buttons.append([
        InlineKeyboardButton(
            f"📤 Send {start}-{end} ({current_count})",
            callback_data=f"imgsend|{token}|{category}|{page}"
        )
    ])

    nav = []

    if page > 0:
        nav.append(
            InlineKeyboardButton(
                "⬅️ Prev",
                callback_data=f"imgpage|{token}|{category}|{page - 1}"
            )
        )

    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"imgpage|{token}|{category}|{page + 1}"
            )
        )

    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(
            "🔙 Categories",
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


def sort_tmdb_images(items):
    try:
        return sorted(
            items,
            key=lambda x: (
                x.get("vote_average") or 0,
                x.get("vote_count") or 0,
                x.get("width") or 0
            ),
            reverse=True
        )
    except Exception:
        return items


def make_categories(movie, data):
    posters = sort_tmdb_images(data.get("posters", []) or [])
    backdrops_data = sort_tmdb_images(data.get("backdrops", []) or [])
    logos = sort_tmdb_images(data.get("logos", []) or [])

    categories = {
        "logos": [],
        "posters_all": [],
        "posters_en": [],
        "posters_hi": [],
        "landscape": [],
        "backdrops": []
    }

    # Main poster
    if movie.get("poster_path"):
        categories["posters_all"].append(tmdb_img_url(movie["poster_path"]))

    # Landscape me sirf main official backdrop
    if movie.get("backdrop_path"):
        categories["landscape"].append(tmdb_img_url(movie["backdrop_path"]))

    # Posters
    for img in posters:
        url = tmdb_img_url(img.get("file_path"))
        if not url:
            continue

        lang = img.get("iso_639_1")

        categories["posters_all"].append(url)

        if lang == "en":
            categories["posters_en"].append(url)

        if lang == "hi":
            categories["posters_hi"].append(url)

    # Backdrops me saare TMDB backdrops
    for img in backdrops_data:
        url = tmdb_img_url(img.get("file_path"))
        if not url:
            continue

        categories["backdrops"].append(url)

    # Logos
    for img in logos:
        url = tmdb_img_url(img.get("file_path"))
        if url:
            categories["logos"].append(url)

    for key in categories:
        categories[key] = remove_duplicates(categories[key])

    return categories


async def send_images(client, chat_id, images, reply_to_message_id=None, message_thread_id=None):
    """
    Album Telegram Bot API se send karega.
    Pyrogram send_media_group use nahi hoga, isliye topics error nahi aayega.
    """
    bot_token = get_bot_token(client)

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(images), 10):
            chunk = images[i:i + 10]

            # Bot API sendMediaGroup minimum 2 media maangta hai
            if len(chunk) == 1:
                api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

                payload = {
                    "chat_id": chat_id,
                    "photo": chunk[0],
                }

                if reply_to_message_id:
                    payload["reply_to_message_id"] = reply_to_message_id
                    payload["allow_sending_without_reply"] = True

                if message_thread_id:
                    payload["message_thread_id"] = message_thread_id

                async with session.post(api_url, json=payload) as resp:
                    result = await resp.json()

                    if not result.get("ok"):
                        raise Exception(result.get("description", "Bot API photo send failed"))

            else:
                api_url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"

                media = []
                for url in chunk:
                    media.append({
                        "type": "photo",
                        "media": url
                    })

                payload = {
                    "chat_id": chat_id,
                    "media": media
                }

                if reply_to_message_id:
                    payload["reply_to_message_id"] = reply_to_message_id
                    payload["allow_sending_without_reply"] = True

                if message_thread_id:
                    payload["message_thread_id"] = message_thread_id

                async with session.post(api_url, json=payload) as resp:
                    result = await resp.json()

                    if not result.get("ok"):
                        raise Exception(result.get("description", "Bot API album send failed"))

            await asyncio.sleep(1)


def page_text(movie, category, page, total):
    title = get_title(movie)
    year = get_year(movie)

    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE + 1
    end = min((page + 1) * PAGE_SIZE, total)

    return (
        f"🎬 **{title}** ({year})\n"
        f"📁 Category: **{category_title(category)}**\n"
        f"🖼 Total Available: **{total}**\n\n"
        f"📄 Page: **{page + 1}/{total_pages}**\n"
        f"📌 Current Images: **{start}-{end}**\n\n"
        f"📤 Send dabao to current 10 images album me send hongi.\n"
        f"Next/Prev se page change kar sakte ho."
    )


@Client.on_message(filters.command("img") & (filters.private | filters.group))
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
        available_categories = {k: v for k, v in categories.items() if v}

        if not available_categories:
            return await msg.edit_text("❌ Is movie ke images nahi mile.")

        token = uuid.uuid4().hex[:10]

        IMG_CACHE[token] = {
            "user_id": message.from_user.id if message.from_user else 0,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "message_thread_id": getattr(message, "message_thread_id", None),
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


@Client.on_callback_query(cb_starts("imgcat|"), group=-999)
async def img_category(client: Client, query: CallbackQuery):
    try:
        cleanup_cache()

        try:
            _, token, category = query.data.split("|")
        except Exception:
            await query.answer("Invalid button.", show_alert=True)
            return

        data = IMG_CACHE.get(token)

        if not data:
            await query.answer(
                "Expired ho gaya. Dobara /img command use karo.",
                show_alert=True
            )
            return

        if query.from_user.id != data["user_id"]:
            await query.answer(
                "Ye buttons tumhare liye nahi hain bro.",
                show_alert=True
            )
            return

        images = data["categories"].get(category, [])

        if not images:
            await query.answer(
                "Is category me images nahi hain.",
                show_alert=True
            )
            return

        page = 0
        total = len(images)

        await query.answer(category_title(category))

        await query.message.edit_text(
            page_text(data["movie"], category, page, total),
            reply_markup=build_page_buttons(token, category, page, total)
        )

    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("imgpage|"), group=-999)
async def img_page(client: Client, query: CallbackQuery):
    try:
        cleanup_cache()

        try:
            _, token, category, page = query.data.split("|")
            page = int(page)
        except Exception:
            await query.answer("Invalid button.", show_alert=True)
            return

        data = IMG_CACHE.get(token)

        if not data:
            await query.answer(
                "Expired ho gaya. Dobara /img command use karo.",
                show_alert=True
            )
            return

        if query.from_user.id != data["user_id"]:
            await query.answer(
                "Ye buttons tumhare liye nahi hain bro.",
                show_alert=True
            )
            return

        images = data["categories"].get(category, [])
        total = len(images)

        if total == 0:
            await query.answer("Images nahi mili.", show_alert=True)
            return

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

        if page < 0:
            page = 0

        if page >= total_pages:
            page = total_pages - 1

        await query.answer(f"Page {page + 1}")

        await query.message.edit_text(
            page_text(data["movie"], category, page, total),
            reply_markup=build_page_buttons(token, category, page, total)
        )

    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("imgsend|"), group=-999)
async def img_send(client: Client, query: CallbackQuery):
    try:
        cleanup_cache()

        try:
            _, token, category, page = query.data.split("|")
            page = int(page)
        except Exception:
            await query.answer("Invalid button.", show_alert=True)
            return

        data = IMG_CACHE.get(token)

        if not data:
            await query.answer(
                "Expired ho gaya. Dobara /img command use karo.",
                show_alert=True
            )
            return

        if query.from_user.id != data["user_id"]:
            await query.answer(
                "Ye buttons tumhare liye nahi hain bro.",
                show_alert=True
            )
            return

        images = data["categories"].get(category, [])
        total = len(images)

        if total == 0:
            await query.answer("Images nahi mili.", show_alert=True)
            return

        start = page * PAGE_SIZE
        end = min(start + PAGE_SIZE, total)

        selected = images[start:end]

        if not selected:
            await query.answer("Is page me images nahi hain.", show_alert=True)
            return

        await query.answer(f"Sending {len(selected)} images...")

        # Button wala message edit/delete nahi hoga
        status = await client.send_message(
            chat_id=query.message.chat.id,
            text=(
                f"⬆️ Uploading **{len(selected)}** images...\n\n"
                f"🎭 Category: **{category_title(category)}**\n"
                f"🖼 Images: **{start + 1}-{end}**"
            ),
            reply_to_message_id=query.message.id
        )

        try:
            await send_images(
                client=client,
                chat_id=query.message.chat.id,
                images=selected,
                reply_to_message_id=data.get("reply_to"),
                message_thread_id=data.get("message_thread_id")
            )

            await status.edit_text(
                f"✅ Sent **{len(selected)}** images.\n\n"
                f"Button wala message delete nahi hoga.\n"
                f"Next/Prev se aur images bhej sakte ho."
            )

        except Exception as e:
            print("SEND ERROR:", e)
            await status.edit_text(
                "❌ Images send nahi hui.\n\n"
                f"`{str(e)[:900]}`"
            )

    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("imgback|"), group=-999)
async def img_back(client: Client, query: CallbackQuery):
    try:
        cleanup_cache()

        try:
            _, token = query.data.split("|")
        except Exception:
            await query.answer("Invalid button.", show_alert=True)
            return

        data = IMG_CACHE.get(token)

        if not data:
            await query.answer(
                "Expired ho gaya. Dobara /img command use karo.",
                show_alert=True
            )
            return

        if query.from_user.id != data["user_id"]:
            await query.answer(
                "Ye buttons tumhare liye nahi hain bro.",
                show_alert=True
            )
            return

        movie = data["movie"]
        categories = data["categories"]

        title = get_title(movie)
        movie_year = get_year(movie)

        await query.answer("Categories")

        await query.message.edit_text(
            f"🎬 **{title}** ({movie_year})\n\n"
            f"Images category select karo:",
            reply_markup=build_category_buttons(token, categories)
        )

    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("imgcancel|"), group=-999)
async def img_cancel(client: Client, query: CallbackQuery):
    try:
        try:
            _, token = query.data.split("|")
        except Exception:
            await query.answer("Invalid button.", show_alert=True)
            return

        data = IMG_CACHE.get(token)

        if data and query.from_user.id != data["user_id"]:
            await query.answer(
                "Ye buttons tumhare liye nahi hain bro.",
                show_alert=True
            )
            return

        IMG_CACHE.pop(token, None)

        await query.answer("Cancelled")
        await query.message.edit_text("❌ Cancelled.")

    finally:
        raise StopPropagation

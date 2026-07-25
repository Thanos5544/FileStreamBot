import os
import time
import uuid
import asyncio
import aiohttp
from typing import Dict, List, Optional

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ==========================================
# ⚙️ CONFIGURATION & CONSTANTS
# ==========================================
WALLHAVEN_API = "https://wallhaven.cc/api/v1/search"
PAGE_SIZE = 10  # Ek baar me 10 HD Wallpapers (Telegram Album Limit)
CACHE_TTL = 1800  # 30 Minutes Cache Expiry
WALL_CACHE: Dict[str, dict] = {}


# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def cleanup_expired_cache():
    """Auto remove expired search sessions."""
    current_time = time.time()
    expired = [k for k, v in WALL_CACHE.items() if current_time - v.get("time", current_time) > CACHE_TTL]
    for k in expired:
        WALL_CACHE.pop(k, None)


def get_bot_token(client: Client) -> str:
    """Safe Bot Token extractor for Direct Telegram API Album Sending."""
    token = (
        os.getenv("BOT_TOKEN")
        or os.getenv("TG_BOT_TOKEN")
        or os.getenv("TOKEN")
        or getattr(client, "bot_token", None)
    )
    if not token:
        raise ValueError("❌ BOT_TOKEN environment variable nahi mila!")
    return token


# ==========================================
# 🌐 WALLHAVEN API FETCHER (1080p to 4K+)
# ==========================================
async def fetch_wallpapers(session: aiohttp.ClientSession, query: str, page: int = 1) -> List[str]:
    """
    Wallhaven se minimum 1920x1080 (Full HD) aur Top Rated wallpapers nikalta hai.
    """
    params = {
        "q": query,
        "categories": "111",      # General, Anime, People sab allowed
        "purity": "100",          # 100% SFW (Safe For Work / Telegram safe)
        "sorting": "toplist",     # Sabse Best & High Rated Pehle
        "order": "desc",
        "atleast": "1920x1080",   # GUARANTEED Full HD & 4K quality!
        "page": page
    }

    try:
        async with session.get(WALLHAVEN_API, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Direct full-resolution image URL extract karna
                results = [item["path"] for item in data.get("data", []) if "path" in item]
                return results[:PAGE_SIZE]
    except Exception as e:
        print(f"Wallhaven API Error: {e}")
    return []


# ==========================================
# 📤 TELEGRAM ALBUM SENDER (DIRECT API)
# ==========================================
async def send_album_via_api(client: Client, chat_id: int, image_urls: List[str], reply_to: Optional[int] = None, thread_id: Optional[int] = None):
    """Bina kisi topic/thread error ke 10 images ka album bhejta hai."""
    bot_token = get_bot_token(client)
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"

    media = [{"type": "photo", "media": url} for url in image_urls]
    payload = {
        "chat_id": chat_id,
        "media": media,
        "allow_sending_without_reply": True
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    if thread_id:
        payload["message_thread_id"] = thread_id

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=payload) as resp:
            res = await resp.json()
            if not res.get("ok"):
                raise Exception(res.get("description", "Telegram API Album Send Failed"))


# ==========================================
# 🎨 UI KEYBOARDS & TEXTS
# ==========================================
def build_wall_keyboard(token: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"🔄 Refresh / Next 10 HD Pics (Page {page + 1})", 
                callback_data=f"wall:next:{token}:{page + 1}"
            )
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data=f"wall:close:{token}")
        ]
    ])


def generate_wall_text(query: str, page: int, count: int) -> str:
    return (
        f"🌌 **Wallhaven HD / 4K Wallpapers**\n\n"
        f"🔎 **Search Tag:** `{query}`\n"
        f"🖼 **Sent Images:** `{count} HD Pics` (Page {page})\n"
        f"⚡ **Quality:** `1080p - 4K Ultra HD`\n\n"
        f"👇 *Niche button daba ke agle 10 naye wallpapers dekho!*"
    )


# ==========================================
# 🤖 PYROGRAM HANDLERS
# ==========================================
@Client.on_message(filters.command(["wall", "wallpaper", "hd"]) & (filters.private | filters.group))
async def wall_command(client: Client, message: Message):
    cleanup_expired_cache()

    # Agar user ne kuch type nahi kiya, toh default killer tags use honge
    if len(message.command) < 2:
        query_str = "anime OR superhero OR cyberpunk OR 4k"
        display_query = "Anime / Superhero / Cyberpunk (Default)"
    else:
        query_str = " ".join(message.command[1:]).strip()
        display_query = query_str

    status_msg = await message.reply_text(f"⚡ **Searching 10 HD Wallpapers for:** `{display_query}`...")

    try:
        async with aiohttp.ClientSession() as session:
            images = await fetch_wallpapers(session, query_str, page=1)

        if not images:
            return await status_msg.edit_text(
                f"❌ **Koi HD Wallpaper nahi mila For:** `{display_query}`\n\n"
                "💡 *Koi dusra naam try karo jaise:* `/wall batman`, `/wall naruto`, ya `/wall iron man`"
            )

        # Cache session store karna taaki refresh button kaam kare
        token = uuid.uuid4().hex[:8]
        WALL_CACHE[token] = {
            "user_id": message.from_user.id if message.from_user else 0,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "thread_id": getattr(message, "message_thread_id", None),
            "query": query_str,
            "display_query": display_query,
            "time": time.time()
        }

        await status_msg.edit_text("📤 **Sending 10 Ultra HD Wallpapers Album...**")

        # Send 10 Images Album
        await send_album_via_api(
            client=client,
            chat_id=message.chat.id,
            image_urls=images,
            reply_to=message.id,
            thread_id=getattr(message, "message_thread_id", None)
        )

        # Edit status message to show Refresh button
        await status_msg.edit_text(
            text=generate_wall_text(display_query, page=1, count=len(images)),
            reply_markup=build_wall_keyboard(token, page=1)
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error Aaya:**\n`{str(e)[:400]}`")


@Client.on_callback_query(filters.regex(r"^wall:"))
async def wall_callback_handler(client: Client, query: CallbackQuery):
    cleanup_expired_cache()
    parts = query.data.split(":")
    action = parts[1]
    token = parts[2]

    session_data = WALL_CACHE.get(token)
    if not session_data:
        return await query.answer("⚠️ Ye session purana ho gaya hai. Dobara /wall command use karo!", show_alert=True)

    # Allow only the person who triggered the command to click (prevent spam)
    if query.from_user.id != session_data["user_id"] and session_data["user_id"] != 0:
        return await query.answer("❌ Bro, ye command tumne nahi lagayi thi. Apni command lagao!", show_alert=True)

    try:
        if action == "close":
            WALL_CACHE.pop(token, None)
            await query.answer("Closed!")
            return await query.message.delete()

        elif action == "next":
            next_page = int(parts[3])
            query_str = session_data["query"]
            display_query = session_data["display_query"]

            await query.answer(f"⚡ Fetching Page {next_page} (Next 10 HD Pics)...")

            # Notification message during upload
            upload_msg = await client.send_message(
                chat_id=query.message.chat.id,
                text=f"🔄 **Downloading & Uploading Next 10 HD Wallpapers (Page {next_page})...**",
                reply_to_message_id=query.message.id
            )

            async with aiohttp.ClientSession() as session:
                images = await fetch_wallpapers(session, query_str, page=next_page)

            if not images:
                await upload_msg.delete()
                return await query.answer("❌ Aur images nahi mili bro! Koi naya topic search karo.", show_alert=True)

            # Send New Album
            await send_album_via_api(
                client=client,
                chat_id=session_data["chat_id"],
                image_urls=images,
                reply_to=session_data["reply_to"],
                thread_id=session_data["thread_id"]
            )

            await upload_msg.delete()

            # Update the existing message button to Page + 1
            await query.message.edit_text(
                text=generate_wall_text(display_query, page=next_page, count=len(images)),
                reply_markup=build_wall_keyboard(token, page=next_page)
            )

    except Exception as e:
        await query.answer("❌ Kuch technical problem aayi!", show_alert=True)
        print(f"Wallhaven Callback Error: {e}")

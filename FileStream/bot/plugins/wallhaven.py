import os
import time
import uuid
import random
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
# ⚙️ CONFIG
# ==========================================
# Optional: Koyeb me WALLHAVEN_API_KEY add karoge to aur zyada results milenge
WALLHAVEN_KEY = os.getenv("WALLHAVEN_API_KEY", "3I4YNfdhia47CD1WKcDszZXrfvBPHOUO")
WALLHAVEN_URL = "https://wallhaven.cc/api/v1/search"

BATCH_SIZE = 10          # Ek album = 10 HD pics
CACHE_TTL = 3600         # 1 hour session
MAX_FETCH_TRY = 5

WALL_CACHE: Dict[str, dict] = {}

DEFAULT_TAGS = [
    "anime", "anime girl", "superhero", "marvel", "dc comics",
    "cyberpunk", "spider-man", "batman", "iron man", "goku",
    "naruto", "one piece", "jujutsu kaisen", "demon slayer",
    "solo leveling", "attack on titan", "movie poster", "4k landscape"
]


# ==========================================
# 🛠️ HELPERS
# ==========================================
def clean_cache():
    now = time.time()
    for k in [k for k, v in WALL_CACHE.items() if now - v.get("time", now) > CACHE_TTL]:
        WALL_CACHE.pop(k, None)


def get_bot_token(client: Client) -> str:
    token = (
        os.getenv("BOT_TOKEN")
        or os.getenv("TG_BOT_TOKEN")
        or os.getenv("TOKEN")
        or getattr(client, "bot_token", None)
    )
    if not token:
        raise ValueError("BOT_TOKEN env nahi mila!")
    return token


# ==========================================
# 🌐 WALLHAVEN API
# ==========================================
async def wh_fetch_page(session: aiohttp.ClientSession, query: str, page: int, seed: str) -> List[dict]:
    params = {
        "q": query,
        "categories": "111",
        "purity": "100",          # SFW only
        "sorting": "random",      # har refresh pe naya maal
        "seed": seed,             # paging consistent rahe
        "atleast": "1920x1080",   # Full HD / 4K guaranteed
        "page": page,
    }
    if WALLHAVEN_KEY:
        params["apikey"] = WALLHAVEN_KEY

    try:
        async with session.get(WALLHAVEN_URL, params=params, timeout=aiohttp.ClientTimeout(total=25)) as r:
            if r.status != 200:
                return []
            data = await r.json()
            return [
                {"url": i["path"], "res": i.get("resolution", "HD")}
                for i in data.get("data", []) if i.get("path")
            ]
    except Exception as e:
        print("Wallhaven fetch error:", e)
        return []


async def get_next_batch(sess: dict) -> List[dict]:
    """Pool se 10 fresh unique wallpapers nikalta hai, kam pade to next page fetch karta hai."""
    pool: List[dict] = sess["pool"]
    seen: set = sess["seen"]

    async with aiohttp.ClientSession() as http:
        tries = 0
        while len(pool) < BATCH_SIZE and tries < MAX_FETCH_TRY:
            tries += 1
            items = await wh_fetch_page(http, sess["query"], sess["api_page"], sess["seed"])
            sess["api_page"] += 1

            if not items:
                # page khatam -> naya seed le kar dobara start
                sess["seed"] = uuid.uuid4().hex[:6]
                sess["api_page"] = 1
                if tries >= 2:
                    break
                continue

            for it in items:
                if it["url"] not in seen:
                    seen.add(it["url"])
                    pool.append(it)

    batch = pool[:BATCH_SIZE]
    del pool[:BATCH_SIZE]
    return batch


# ==========================================
# 📤 ALBUM SENDER (Direct Bot API = no topic bug)
# ==========================================
async def send_album(client: Client, chat_id: int, items: List[dict], thread_id: Optional[int] = None):
    token = get_bot_token(client)
    base = f"https://api.telegram.org/bot{token}"
    urls = [i["url"] for i in items]

    async with aiohttp.ClientSession() as http:
        payload = {"chat_id": chat_id}
        if thread_id:
            payload["message_thread_id"] = thread_id

        if len(urls) == 1:
            payload["photo"] = urls[0]
            async with http.post(f"{base}/sendPhoto", json=payload) as r:
                res = await r.json()
                if not res.get("ok"):
                    raise Exception(res.get("description"))
            return

        payload["media"] = [{"type": "photo", "media": u} for u in urls]
        async with http.post(f"{base}/sendMediaGroup", json=payload) as r:
            res = await r.json()

        if res.get("ok"):
            return

        # Fallback: agar koi ek image reject ho jaye to ek-ek karke bhejo
        for u in urls:
            p = {"chat_id": chat_id, "photo": u}
            if thread_id:
                p["message_thread_id"] = thread_id
            try:
                await http.post(f"{base}/sendPhoto", json=p)
                await asyncio.sleep(0.4)
            except Exception:
                pass


# ==========================================
# 🎨 UI
# ==========================================
def wall_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Next 10 HD Wallpapers", callback_data=f"wl:next:{token}")],
        [
            InlineKeyboardButton("🎲 Random Topic", callback_data=f"wl:rand:{token}"),
            InlineKeyboardButton("❌ Close", callback_data=f"wl:close:{token}")
        ]
    ])


def wall_text(sess: dict, count: int) -> str:
    return (
        f"✅ **{count} Ultra HD Wallpapers Sent!**\n\n"
        f"🔎 **Topic:** `{sess['query']}`\n"
        f"📦 **Batch:** `#{sess['batch_no']}`  |  📊 **Total:** `{sess['total_sent']}`\n"
        f"⚡ **Quality:** `1080p → 4K`\n\n"
        f"👇 Button dabao aur agle **10 naye** wallpaper lo!"
    )


# ==========================================
# 🤖 /wall COMMAND
# ==========================================
@Client.on_message(filters.command(["wall", "wallpaper", "hd"]) & (filters.private | filters.group))
async def wall_cmd(client: Client, message: Message):
    clean_cache()

    if len(message.command) > 1:
        query = " ".join(message.command[1:]).strip()
    else:
        query = random.choice(DEFAULT_TAGS)

    status = await message.reply_text(f"⚡ **Fetching 10 HD Wallpapers...**\n🔎 `{query}`")

    token = uuid.uuid4().hex[:8]
    sess = {
        "user_id": message.from_user.id if message.from_user else 0,
        "chat_id": message.chat.id,
        "thread_id": getattr(message, "message_thread_id", None),
        "query": query,
        "seed": uuid.uuid4().hex[:6],
        "api_page": 1,
        "pool": [],
        "seen": set(),
        "batch_no": 1,
        "total_sent": 0,
        "time": time.time(),
    }
    WALL_CACHE[token] = sess

    batch = await get_next_batch(sess)

    if not batch:
        WALL_CACHE.pop(token, None)
        return await status.edit_text(
            f"❌ **`{query}` ke liye kuch nahi mila.**\n\n"
            "💡 Try: `/wall naruto` • `/wall batman` • `/wall cyberpunk`"
        )

    try:
        await send_album(client, sess["chat_id"], batch, sess["thread_id"])
        sess["total_sent"] += len(batch)

        await status.delete()

        # Button ALWAYS album ke niche
        await client.send_message(
            chat_id=sess["chat_id"],
            text=wall_text(sess, len(batch)),
            reply_markup=wall_keyboard(token),
            message_thread_id=sess["thread_id"]
        ) if sess["thread_id"] else await client.send_message(
            chat_id=sess["chat_id"],
            text=wall_text(sess, len(batch)),
            reply_markup=wall_keyboard(token)
        )

    except Exception as e:
        await status.edit_text(f"❌ **Send Failed:**\n`{str(e)[:300]}`")


# ==========================================
# 🔘 CALLBACKS
# ==========================================
@Client.on_callback_query(filters.regex(r"^wl:"))
async def wall_cb(client: Client, query: CallbackQuery):
    clean_cache()
    _, action, token = query.data.split(":")

    sess = WALL_CACHE.get(token)
    if not sess:
        return await query.answer("⚠️ Session expire ho gaya, dobara /wall karo!", show_alert=True)

    if sess["user_id"] and query.from_user.id != sess["user_id"]:
        return await query.answer("❌ Ye tumhari request nahi hai bro!", show_alert=True)

    if action == "close":
        WALL_CACHE.pop(token, None)
        await query.answer("Closed ✅")
        return await query.message.delete()

    if action == "rand":
        sess["query"] = random.choice(DEFAULT_TAGS)
        sess["seed"] = uuid.uuid4().hex[:6]
        sess["api_page"] = 1
        sess["pool"].clear()
        sess["seen"].clear()
        await query.answer(f"🎲 New Topic: {sess['query']}")
    else:
        await query.answer("⚡ Loading next 10...")

    # Purana button message hata do (taaki naya button album ke niche aaye)
    try:
        await query.message.delete()
    except Exception:
        pass

    loading = await client.send_message(
        sess["chat_id"],
        f"⏳ **Loading 10 fresh HD wallpapers...**\n🔎 `{sess['query']}`"
    )

    batch = await get_next_batch(sess)

    if not batch:
        return await loading.edit_text(
            "❌ **Aur wallpapers nahi mile!**\n💡 Naya topic try karo: `/wall <name>`",
            reply_markup=wall_keyboard(token)
        )

    try:
        await send_album(client, sess["chat_id"], batch, sess["thread_id"])
        sess["batch_no"] += 1
        sess["total_sent"] += len(batch)
        sess["time"] = time.time()

        await loading.delete()

        await client.send_message(
            chat_id=sess["chat_id"],
            text=wall_text(sess, len(batch)),
            reply_markup=wall_keyboard(token)
        )
    except Exception as e:
        await loading.edit_text(f"❌ **Error:** `{str(e)[:300]}`")

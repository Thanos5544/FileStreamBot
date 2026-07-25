import os
import io
import time
import json
import uuid
import random
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional

from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyParameters
)

# Setup Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ==========================================
# ⚙️ CONFIG
# ==========================================
# Set your key in Environment Variables or leave empty
WALLHAVEN_KEY = os.getenv("WALLHAVEN_API_KEY", "3I4YNfdhia47CD1WKcDszZXrfvBPHOUO")
WH_URL = "https://wallhaven.cc/api/v1/search"

BATCH = 10
CACHE_TTL = 3600
TG_PHOTO_LIMIT = 9 * 1024 * 1024      # 9MB limit for photos
TG_DOC_LIMIT = 45 * 1024 * 1024       # 45MB limit for docs

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://wallhaven.cc/",
}

WALL_CACHE: Dict[str, dict] = {}

# Categories inspired by Wallhaven screenshot
CATEGORIES = [
    "Anime", "Nature", "Cyberpunk", "Abstract", "Pixel Art", 
    "Dark", "Landscape", "Space", "Cars", "Gaming", 
    "Minimalism", "Fantasy", "Ocean", "City"
]

# Default fallback tags
TAGS = ["anime", "cyberpunk", "nature", "space", "landscape"]

# ==========================================
# 🛠️ HELPERS
# ==========================================

def clean_cache():
    now = time.time()
    for k in [k for k, v in WALL_CACHE.items() if now - v.get("time", now) > CACHE_TTL]:
        WALL_CACHE.pop(k, None)

def bot_token(client: Client) -> str:
    t = os.getenv("BOT_TOKEN") or getattr(client, "bot_token", None)
    if not t:
        raise ValueError("BOT_TOKEN not found!")
    return t

async def compress_photo(raw: bytes) -> Optional[bytes]:
    """Iteratively compress image to fit Telegram limits."""
    if not PIL_OK:
        return raw
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        # Start with high quality
        for max_dim in (3840, 2560, 1920):
            im.thumbnail((max_dim, max_dim))
            for quality in [85, 75, 60]:
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=quality, optimize=True)
                if len(buf.getvalue()) <= TG_PHOTO_LIMIT:
                    return buf.getvalue()
        return raw # Fallback to raw if compression fails
    except Exception as e:
        log.error(f"Compression error: {e}")
        return raw

# ==========================================
# 🌐 WALLHAVEN API
# ==========================================

async def wh_page(http, query: str, page: int, seed: str) -> List[dict]:
    params = {
        "q": query, "categories": "111", "purity": "100",
        "sorting": "random", "seed": seed,
        "atleast": "1920x1080", "page": page,
    }
    if WALLHAVEN_KEY:
        params["apikey"] = WALLHAVEN_KEY
    
    try:
        async with http.get(WH_URL, params=params, headers=HEADERS,
                            timeout=aiohttp.ClientTimeout(total=25)) as r:
            if r.status == 429:
                log.warning("Wallhaven Rate Limited (429)")
                return []
            if r.status != 200:
                return []
            d = await r.json()
            return [{
                "url": i["path"],
                "res": i.get("resolution", "HD"),
                "id": i.get("id", ""),
                "name": i.get("path", "").split("/")[-1],
                "size": i.get("file_size", 0),
            } for i in d.get("data", []) if i.get("path")]
    except Exception as e:
        log.error(f"WH fetch error: {e}")
        return []

async def next_batch(sess: dict) -> List[dict]:
    pool, seen = sess["pool"], sess["seen"]
    async with aiohttp.ClientSession() as http:
        tries = 0
        while len(pool) < BATCH and tries < 5:
            tries += 1
            items = await wh_page(http, sess["query"], sess["api_page"], sess["seed"])
            sess["api_page"] += 1
            if not items:
                sess["seed"] = uuid.uuid4().hex[:6]
                sess["api_page"] = 1
                continue
            for it in items:
                if it["url"] not in seen:
                    seen.add(it["url"])
                    pool.append(it)
        return pool[:BATCH]

async def dl_image(http, item: dict) -> Optional[dict]:
    try:
        async with http.get(item["url"], headers=HEADERS,
                            timeout=aiohttp.ClientTimeout(total=60)) as r:
            if r.status != 200: return None
            raw = await r.read()
            
            item["raw"] = raw
            # Handle compression
            if len(raw) > TG_PHOTO_LIMIT:
                item["photo"] = await compress_photo(raw)
            else:
                item["photo"] = raw
            return item
    except Exception:
        return None

async def download_all(items: List[dict]) -> List[dict]:
    conn = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=conn) as http:
        res = await asyncio.gather(*[dl_image(http, i) for i in items])
    return [r for r in res if r and r.get("photo")]

# ==========================================
# 📤 SENDING LOGIC
# ==========================================

async def send_album(client: Client, chat_id: int, items: List[dict], thread_id: Optional[int] = None):
    tk = bot_token(client)
    url = f"https://api.telegram.org/bot{tk}/sendMediaGroup"
    form = aiohttp.FormData()
    form.add_field("chat_id", str(chat_id))
    if thread_id: form.add_field("message_thread_id", str(thread_id))

    media = []
    for idx, it in enumerate(items):
        key = f"f{idx}"
        media.append({"type": "photo", "media": f"attach://{key}"})
        form.add_field(key, it["photo"], filename=f"{idx}.jpg", content_type="image/jpeg")
    form.add_field("media", json.dumps(media))

    async with aiohttp.ClientSession() as http:
        async with http.post(url, data=form, timeout=aiohttp.ClientTimeout(total=300)) as r:
            res = await r.json()
            if not res.get("ok"): raise Exception(res.get("description"))
            return [m["message_id"] for m in res.get("result", [])]

async def send_docs(client: Client, chat_id: int, items: List[dict], thread_id: Optional[int] = None):
    tk = bot_token(client)
    url = f"https://api.telegram.org/bot{tk}/sendMediaGroup"
    ids = []
    valid = [i for i in items if i.get("raw") and len(i["raw"]) <= TG_DOC_LIMIT]

    for c in range(0, len(valid), BATCH):
        chunk = valid[c:c + BATCH]
        form = aiohttp.FormData()
        form.add_field("chat_id", str(chat_id))
        if thread_id: form.add_field("message_thread_id", str(thread_id))

        media = []
        for idx, it in enumerate(chunk):
            key = f"d{idx}"
            media.append({"type": "document", "media": f"attach://{key}", "caption": f"🖼 {it['res']}"})
            form.add_field(key, it["raw"], filename=it["name"], content_type="application/octet-stream")
        form.add_field("media", json.dumps(media))

        async with aiohttp.ClientSession() as http:
            async with http.post(url, data=form, timeout=aiohttp.ClientTimeout(total=600)) as r:
                res = await r.json()
                if res.get("ok"): ids += [m["message_id"] for m in res["result"]]
        await asyncio.sleep(1)
    return ids

# ==========================================
# 🎨 UI COMPONENTS
# ==========================================

def menu_kb() -> InlineKeyboardMarkup:
    """The Main Category Menu"""
    buttons = []
    # Create a 2-column grid for categories
    for i in range(0, len(CATEGORIES), 2):
        row = [InlineKeyboardButton(CATEGORIES[i], callback_data=f"wl:cat:{CATEGORIES[i].lower()}")]
        if i + 1 < len(CATEGORIES):
            row.append(InlineKeyboardButton(CATEGORIES[i+1], callback_data=f"wl:cat:{CATEGORIES[i+1].lower()}"))
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🎲 Random Topic", callback_data="wl:rnd:none")])
    return InlineKeyboardMarkup(buttons)

def album_kb(token: str) -> InlineKeyboardMarkup:
    """Buttons that appear under an active album"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh New Album", callback_data=f"wl:ref:{token}")],
        [InlineKeyboardButton("📥 Download 4K Files", callback_data=f"wl:dl:{token}")],
        [InlineKeyboardButton("❌ Close Album", callback_data=f"wl:cls:{token}")]
    ])

def caption_text(s: dict, n: int) -> str:
    top_res = s["items"][0]["res"] if s["items"] else "4K"
    return (
        f"🌌 **{n} Ultra HD Wallpapers**\n\n"
        f"🔎 **Topic:** `{s['query']}`\n"
        f"📦 **Album:** `#{s['batch_no']}` | ⚡ **Res:** `{top_res}`\n"
        f"📊 **Total Sent:** `{s['total']}`\n\n"
        f"🔄 *Refresh* = Change entire album\n"
        f"📥 *Download* = Original 4K files"
    )

async def wipe_messages(client: Client, chat_id: int, ids: List[int]):
    if not ids: return
    try:
        await client.delete_messages(chat_id, ids)
    except Exception:
        pass

# ==========================================
# 🤖 COMMANDS & CALLBACKS
# ==========================================

@Client.on_message(filters.command(["wall", "wallpaper", "hd"]) & (filters.private | filters.group))
async def wall_cmd(client: Client, m: Message):
    clean_cache()
    
    # Scenario 1: User just types /wall (Show Menu)
    if len(m.command) == 1:
        text = (
            "**Welcome to HD Wallpapers! 🌌**\n\n"
            "🔍 **How to search?**\n"
            "Type `/wall [topic]` to find anything! (e.g., `/wall ocean`)\n\n"
            "Or pick a category below to explore: 👇"
        )
        await m.reply_text(text, reply_markup=menu_kb())
        return

    # Scenario 2: User types /wall <query>
    query = " ".join(m.command[1:]).strip()
    st = await m.reply_text(f"⚡ **Searching for...**\n🔎 `{query}`")
    
    token = uuid.uuid4().hex[:8]
    s = {
        "user_id": m.from_user.id if m.from_user else 0,
        "chat_id": m.chat.id,
        "thread_id": getattr(m, "message_thread_id", None),
        "query": query, "seed": uuid.uuid4().hex[:6], "api_page": 1,
        "pool": [], "seen": set(), "items": [],
        "album_ids": [], "btn_id": None,
        "batch_no": 1, "total": 0, "time": time.time(),
        "busy": False
    }
    WALL_CACHE[token] = s
    await deliver(client, s, token, st)

async def deliver(client: Client, s: dict, token: str, status: Message) -> bool:
    if s.get("busy"): return False
    s["busy"] = True
    
    try:
        batch = await next_batch(s)
        if not batch:
            await status.edit_text(f"❌ No results found for `{s['query']}`.\nTry another topic!")
            s["busy"] = False
            return False

        await status.edit_text(f"⬇️ **Downloading {len(batch)} HD images...**")
        items = await download_all(batch)
        if not items:
            await status.edit_text("❌ Download failed. Try again.")
            s["busy"] = False
            return False

        await status.edit_text(f"📤 **Uploading album...**")
        ids = await send_album(client, s["chat_id"], items, s["thread_id"])

        s["items"] = items
        s["album_ids"] = ids
        s["total"] += len(items)
        s["time"] = time.time()

        try: await status.delete()
        except: pass

        btn = await client.send_message(
            chat_id=s["chat_id"],
            text=caption_text(s, len(items)),
            reply_markup=album_kb(token),
            reply_to_message_id=ids[0] if ids else None
        )
        s["btn_id"] = btn.id
        return True

    except Exception as e:
        log.error(f"Deliver error: {e}")
        try: await status.edit_text(f"❌ **Error:** `{str(e)[:200]}`")
        except: pass
        return False
    finally:
        s["busy"] = False

@Client.on_callback_query(filters.regex(r"^wl:"))
async def wall_cb(client: Client, q: CallbackQuery):
    clean_cache()
    _, act, token_or_cat = q.data.split(":", 2)

    # Logic for Menu Clicks (wl:cat:category)
    if act == "cat":
        # Check if this is a category click or a real session token
        # Since categories don't have tokens, we create a temporary session
        query = token_or_cat
        s = {
            "user_id": q.from_user.id,
            "chat_id": q.message.chat.id,
            "thread_id": getattr(q.message, "message_thread_id", None),
            "query": query, "seed": uuid.uuid4().hex[:6], "api_page": 1,
            "pool": [], "seen": set(), "items": [],
            "album_ids": [], "btn_id": None,
            "batch_no": 1, "total": 0, "time": time.time(),
            "busy": False
        }
        token = uuid.uuid4().hex[:8]
        WALL_CACHE[token] = s
        
        await q.answer(f"🔍 Searching: {query.title()}")
        st = await client.send_message(s["chat_id"], f"⚡ **Loading `{query}`...**")
        await deliver(client, s, token, st)
        return

    # Logic for existing sessions
    s = WALL_CACHE.get(token_or_cat)
    if not s:
        return await q.answer("⚠️ Session expired! Use /wall again.", show_alert=True)
    
    if s["user_id"] and q.from_user.id != s["user_id"]:
        return await q.answer("❌ This is not your session!", show_alert=True)

    if s["busy"]:
        return await q.answer("⏳ Please wait, processing...", show_alert=True)

    # ---- CLOSE ----
    if act == "cls":
        await q.answer("Closed ✅")
        await wipe_messages(client, s["chat_id"], s["album_ids"])
        WALL_CACHE.pop(token_or_cat, None)
        try: await q.message.delete()
        except: pass
        return

    # ---- DOWNLOAD ----
    if act == "dl":
        await q.answer("📥 Sending original files...")
        note = await client.send_message(s["chat_id"], "📦 **Uploading original 4K files...**")
        try:
            await send_docs(client, s["chat_id"], s["items"], s["thread_id"])
            await note.edit_text("✅ **Original 4K files sent!**")
        except Exception as e:
            await note.edit_text(f"❌ `{str(e)[:200]}`")
        return

    # ---- RANDOM ----
    if act == "rnd":
        s["query"] = random.choice(TAGS)
        s["seed"] = uuid.uuid4().hex[:6]
        s["api_page"] = 1
        s["pool"].clear()
        s["seen"].clear()
        await q.answer(f"🎲 Topic: {s['query']}")
    else:
        # REFRESH
        await q.answer("🔄 Refreshing album...")
        s["seed"] = uuid.uuid4().hex[:6]

    # Wipe old album
    await wipe_messages(client, s["chat_id"], s["album_ids"])
    s["album_ids"] = []
    try: await q.message.delete()
    except: pass

    st = await client.send_message(s["chat_id"], f"⚡ **Loading new album...**\n🔎 `{s['query']}`")
    s["batch_no"] += 1
    await deliver(client, s, token_or_cat, st)

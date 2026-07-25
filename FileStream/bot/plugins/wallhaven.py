import os
import io
import time
import json
import uuid
import random
import asyncio
import aiohttp
from typing import Dict, List, Optional

from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ==========================================
# ⚙️ CONFIG
# ==========================================
WALLHAVEN_KEY = os.getenv("WALLHAVEN_API_KEY", "3I4YNfdhia47CD1WKcDszZXrfvBPHOUO")
WH_URL = "https://wallhaven.cc/api/v1/search"

BATCH = 10
CACHE_TTL = 3600
TG_PHOTO_LIMIT = 9 * 1024 * 1024      # 9MB safe limit for photos
TG_DOC_LIMIT = 45 * 1024 * 1024       # 45MB for documents

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://wallhaven.cc/",
}

WALL_CACHE: Dict[str, dict] = {}

TAGS = [
    "anime", "anime girl", "superhero", "marvel", "dc comics", "cyberpunk",
    "spider-man", "batman", "iron man", "goku", "naruto", "one piece",
    "jujutsu kaisen", "demon slayer", "solo leveling", "attack on titan",
    "sci-fi movie", "4k landscape", "samurai", "neon city"
]


# ==========================================
# 🛠️ HELPERS
# ==========================================
def clean_cache():
    now = time.time()
    for k in [k for k, v in WALL_CACHE.items() if now - v.get("time", now) > CACHE_TTL]:
        WALL_CACHE.pop(k, None)


def bot_token(client: Client) -> str:
    t = (os.getenv("BOT_TOKEN") or os.getenv("TG_BOT_TOKEN")
         or os.getenv("TOKEN") or getattr(client, "bot_token", None))
    if not t:
        raise ValueError("BOT_TOKEN env nahi mila!")
    return t


# ==========================================
# 🌐 WALLHAVEN FETCH
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
            if r.status != 200:
                return []
            d = await r.json()
            return [{
                "url": i["path"],
                "res": i.get("resolution", "HD"),
                "id": i.get("id", ""),
                "page": i.get("url", ""),
                "size": i.get("file_size", 0),
            } for i in d.get("data", []) if i.get("path")]
    except Exception as e:
        print("WH fetch:", e)
        return []


async def next_batch(sess: dict) -> List[dict]:
    pool, seen = sess["pool"], sess["seen"]
    async with aiohttp.ClientSession() as http:
        tries = 0
        while len(pool) < BATCH and tries < 6:
            tries += 1
            items = await wh_page(http, sess["query"], sess["api_page"], sess["seed"])
            sess["api_page"] += 1
            if not items:
                sess["seed"] = uuid.uuid4().hex[:6]
                sess["api_page"] = 1
                if tries >= 3:
                    break
                continue
            for it in items:
                if it["url"] not in seen:
                    seen.add(it["url"])
                    pool.append(it)
    out = pool[:BATCH]
    del pool[:BATCH]
    return out


# ==========================================
# ⬇️ IMAGE DOWNLOADER (Referer fix)
# ==========================================
async def dl_image(http, item: dict) -> Optional[dict]:
    try:
        async with http.get(item["url"], headers=HEADERS,
                            timeout=aiohttp.ClientTimeout(total=60)) as r:
            if r.status != 200:
                return None
            raw = await r.read()
    except Exception:
        return None

    item["raw"] = raw
    item["name"] = item["url"].split("/")[-1]

    # Photo version (compressed if needed)
    photo = raw
    if len(raw) > TG_PHOTO_LIMIT and PIL_OK:
        try:
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            im.thumbnail((3840, 3840))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=88, optimize=True)
            photo = buf.getvalue()
        except Exception:
            photo = None
    elif len(raw) > TG_PHOTO_LIMIT:
        photo = None

    item["photo"] = photo
    return item


async def download_all(items: List[dict]) -> List[dict]:
    conn = aiohttp.TCPConnector(limit=6)
    async with aiohttp.ClientSession(connector=conn) as http:
        res = await asyncio.gather(*[dl_image(http, i) for i in items])
    return [r for r in res if r and r.get("photo")]


# ==========================================
# 📤 REAL ALBUM SENDER (multipart)
# ==========================================
async def send_album(client: Client, chat_id: int, items: List[dict],
                     thread_id: Optional[int] = None) -> List[int]:
    tk = bot_token(client)
    url = f"https://api.telegram.org/bot{tk}/sendMediaGroup"

    form = aiohttp.FormData()
    form.add_field("chat_id", str(chat_id))
    if thread_id:
        form.add_field("message_thread_id", str(thread_id))

    media = []
    for idx, it in enumerate(items):
        key = f"f{idx}"
        media.append({"type": "photo", "media": f"attach://{key}"})
        form.add_field(key, it["photo"], filename=f"{idx}.jpg",
                       content_type="image/jpeg")
    form.add_field("media", json.dumps(media))

    async with aiohttp.ClientSession() as http:
        async with http.post(url, data=form,
                             timeout=aiohttp.ClientTimeout(total=300)) as r:
            res = await r.json()

    if not res.get("ok"):
        raise Exception(res.get("description", "Album send failed"))
    return [m["message_id"] for m in res.get("result", [])]


async def send_docs(client: Client, chat_id: int, items: List[dict],
                    thread_id: Optional[int] = None) -> List[int]:
    """Original 4K files (uncompressed)."""
    tk = bot_token(client)
    url = f"https://api.telegram.org/bot{tk}/sendMediaGroup"
    ids = []

    valid = [i for i in items if i.get("raw") and len(i["raw"]) <= TG_DOC_LIMIT]

    for c in range(0, len(valid), BATCH):
        chunk = valid[c:c + BATCH]
        form = aiohttp.FormData()
        form.add_field("chat_id", str(chat_id))
        if thread_id:
            form.add_field("message_thread_id", str(thread_id))

        media = []
        for idx, it in enumerate(chunk):
            key = f"d{idx}"
            media.append({
                "type": "document",
                "media": f"attach://{key}",
                "caption": f"🖼 {it['res']}"
            })
            form.add_field(key, it["raw"], filename=it["name"],
                           content_type="application/octet-stream")
        form.add_field("media", json.dumps(media))

        async with aiohttp.ClientSession() as http:
            async with http.post(url, data=form,
                                 timeout=aiohttp.ClientTimeout(total=600)) as r:
                res = await r.json()
        if res.get("ok"):
            ids += [m["message_id"] for m in res["result"]]
        await asyncio.sleep(1)
    return ids


# ==========================================
# 🎨 UI
# ==========================================
def kb(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Album (New 10)", callback_data=f"wl:ref:{token}")],
        [InlineKeyboardButton("📥 Download 4K Files", callback_data=f"wl:dl:{token}")],
        [
            InlineKeyboardButton("🎲 Random Topic", callback_data=f"wl:rnd:{token}"),
            InlineKeyboardButton("❌ Close", callback_data=f"wl:cls:{token}")
        ]
    ])


def cap(s: dict, n: int) -> str:
    top = s["items"][0]["res"] if s["items"] else "4K"
    return (
        f"🌌 **{n} Ultra HD Wallpapers**\n\n"
        f"🔎 **Topic:** `{s['query']}`\n"
        f"📦 **Album:** `#{s['batch_no']}`   ⚡ **Max Res:** `{top}`\n"
        f"📊 **Total Sent:** `{s['total']}`\n\n"
        f"🔄 Refresh = **puri album change**\n"
        f"📥 Download = **original 4K files**"
    )


async def wipe(client: Client, chat_id: int, ids: List[int]):
    for i in ids:
        try:
            await client.delete_messages(chat_id, i)
        except Exception:
            pass


# ==========================================
# 🤖 /wall
# ==========================================
@Client.on_message(filters.command(["wall", "wallpaper", "hd"]) & (filters.private | filters.group))
async def wall_cmd(client: Client, m: Message):
    clean_cache()
    query = " ".join(m.command[1:]).strip() if len(m.command) > 1 else random.choice(TAGS)

    st = await m.reply_text(f"⚡ **Fetching 10 HD Wallpapers...**\n🔎 `{query}`")

    token = uuid.uuid4().hex[:8]
    s = {
        "user_id": m.from_user.id if m.from_user else 0,
        "chat_id": m.chat.id,
        "thread_id": getattr(m, "message_thread_id", None),
        "query": query, "seed": uuid.uuid4().hex[:6], "api_page": 1,
        "pool": [], "seen": set(), "items": [],
        "album_ids": [], "btn_id": None,
        "batch_no": 1, "total": 0, "time": time.time(),
    }
    WALL_CACHE[token] = s

    ok = await deliver(client, s, token, st)
    if not ok:
        WALL_CACHE.pop(token, None)


async def deliver(client: Client, s: dict, token: str, status: Message) -> bool:
    """Fetch → Download → Album → Buttons below."""
    try:
        batch = await next_batch(s)
        if not batch:
            await status.edit_text(
                f"❌ **`{s['query']}` pe kuch nahi mila.**\n"
                "💡 Try: `/wall naruto` • `/wall batman` • `/wall cyberpunk`")
            return False

        await status.edit_text(f"⬇️ **Downloading {len(batch)} HD images...**")
        items = await download_all(batch)
        if not items:
            await status.edit_text("❌ **Download fail ho gaya, dobara try karo.**")
            return False

        await status.edit_text(f"📤 **Uploading album ({len(items)} pics)...**")
        ids = await send_album(client, s["chat_id"], items, s["thread_id"])

        s["items"] = items
        s["album_ids"] = ids
        s["total"] += len(items)
        s["time"] = time.time()

        try:
            await status.delete()
        except Exception:
            pass

        btn = await client.send_message(
            chat_id=s["chat_id"],
            text=cap(s, len(items)),
            reply_markup=kb(token),
            reply_to_message_id=ids[0] if ids else None
        )
        s["btn_id"] = btn.id
        return True

    except Exception as e:
        try:
            await status.edit_text(f"❌ **Error:** `{str(e)[:350]}`")
        except Exception:
            pass
        return False


# ==========================================
# 🔘 CALLBACKS
# ==========================================
@Client.on_callback_query(filters.regex(r"^wl:"))
async def wall_cb(client: Client, q: CallbackQuery):
    clean_cache()
    _, act, token = q.data.split(":")

    s = WALL_CACHE.get(token)
    if not s:
        return await q.answer("⚠️ Session expire! Dobara /wall karo.", show_alert=True)
    if s["user_id"] and q.from_user.id != s["user_id"]:
        return await q.answer("❌ Ye tumhari request nahi hai bro!", show_alert=True)

    # ---- CLOSE ----
    if act == "cls":
        await q.answer("Closed ✅")
        await wipe(client, s["chat_id"], s["album_ids"])
        WALL_CACHE.pop(token, None)
        try:
            await q.message.delete()
        except Exception:
            pass
        return

    # ---- DOWNLOAD 4K ----
    if act == "dl":
        await q.answer("📥 Original 4K files bhej raha hoon...")
        note = await client.send_message(s["chat_id"], "📦 **Uploading original 4K files...**")
        try:
            await send_docs(client, s["chat_id"], s["items"], s["thread_id"])
            await note.edit_text("✅ **Original 4K files sent!** (Uncompressed quality)")
        except Exception as e:
            await note.edit_text(f"❌ `{str(e)[:250]}`")
        return

    # ---- RANDOM TOPIC ----
    if act == "rnd":
        s["query"] = random.choice(TAGS)
        s["seed"] = uuid.uuid4().hex[:6]
        s["api_page"] = 1
        s["pool"].clear()
        s["seen"].clear()
        await q.answer(f"🎲 {s['query'].title()}")
    else:
        await q.answer("🔄 Puri album change ho rahi hai...")
        s["seed"] = uuid.uuid4().hex[:6]

    # ---- REFRESH: purani poori album delete ----
    await wipe(client, s["chat_id"], s["album_ids"])
    s["album_ids"] = []
    try:
        await q.message.delete()
    except Exception:
        pass

    st = await client.send_message(
        s["chat_id"], f"⚡ **Loading new album...**\n🔎 `{s['query']}`")

    s["batch_no"] += 1
    await deliver(client, s, token, st)

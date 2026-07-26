import re
import time
import math
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message

# ==========================================
# 🌐 PIPED API INSTANCES
# ==========================================
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.leptons.xyz",
    "https://pipedapi.r4fo.com",
    "https://pipedapi.pufe.org",
    "https://pipedapi.mha.fi",
    "https://pipedapi.privacy.com.de",
    "https://api.piped.yt",
]

# ==========================================
# 🛠️ HELPERS
# ==========================================
def humanbytes(size):
    if not size: return ""
    power = 2**10; n = 0
    D = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power: size /= power; n += 1
    return str(round(size, 2)) + " " + D.get(n, '') + 'B'

def time_fmt(ms):
    s, ms = divmod(int(ms), 1000)
    m, s = divmod(s, 60); h, m = divmod(m, 60); d, h = divmod(h, 24)
    t = ((f"{d}d, ") if d else "") + ((f"{h}h, ") if h else "") + \
        ((f"{m}m, ") if m else "") + (f"{s}s" if s else "")
    return t or "0s"

async def progress(cur, tot, ud, msg, start):
    now = time.time(); diff = now - start
    if round(diff % 4) == 0 or cur == tot:
        pct = cur * 100 / tot
        spd = cur / diff if diff > 0 else 0
        eta = (tot - cur) / spd * 1000 if spd > 0 else 0
        bar = "█" * int(pct // 10) + "░" * (10 - int(pct // 10))
        txt = f"[{bar}] **{pct:.1f}%**\n{humanbytes(cur)} / {humanbytes(tot)}\nSpeed: {humanbytes(spd)}/s | ETA: {time_fmt(eta)}"
        try: await msg.edit_text(f"⏳ **{ud}**\n\n{txt}")
        except Exception: pass

def extract_yt_id(url):
    m = re.search(r"(?:v=|\/|youtu\.be\/|shorts\/|embed\/)([0-9A-Za-z_-]{11})", url)
    return m.group(1) if m else None

# ==========================================
# 🚀 PIPED API SE DIRECT STREAM URL
# ==========================================
async def get_piped_stream(url):
    video_id = extract_yt_id(url)
    if not video_id:
        return None

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    async with aiohttp.ClientSession() as session:
        for instance in PIPED_INSTANCES:
            try:
                print(f"🔄 Trying {instance}...")
                async with session.get(
                    f"{instance}/streams/{video_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        print(f"  ❌ Status {resp.status}")
                        continue
                    
                    data = await resp.json()
                    title = data.get("title", "Video")
                    thumb = data.get("thumbnailUrl")
                    duration = data.get("duration", 0)
                    uploader = data.get("uploader", "Unknown")

                    # Find best MP4 stream WITH audio (not videoOnly)
                    best = None
                    for s in data.get("videoStreams", []):
                        if s.get("videoOnly"):
                            continue
                        mime = s.get("mimeType", "")
                        if "mp4" in mime.lower() or s.get("format") == "MP4":
                            q = s.get("quality", "")
                            if any(x in q for x in ["720", "480", "360"]):
                                best = s
                                break
                            elif not best:
                                best = s

                    # Fallback: any stream with audio
                    if not best:
                        for s in data.get("videoStreams", []):
                            if not s.get("videoOnly"):
                                best = s
                                break

                    if best and best.get("url"):
                        print(f"✅ Found via {instance} — {best.get('quality')}")
                        return {
                            "url": best["url"],
                            "title": title,
                            "thumb": thumb,
                            "duration": duration,
                            "uploader": uploader,
                            "quality": best.get("quality", "?"),
                        }
            except Exception as e:
                print(f"  ❌ {instance}: {e}")
                continue

    return None

# ==========================================
# 🤖 /dl COMMAND
# ==========================================
@Client.on_message(filters.command(["dl", "yt", "video"]) & (filters.private | filters.group))
async def yt_download_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ **Link do bhai!**\n`/dl https://youtu.be/xxx`")

    url = message.command[1].strip()
    status = await message.reply_text("🔎 **Video dhoondh raha hoon...**")

    try:
        stream = await get_piped_stream(url)

        if not stream:
            return await status.edit_text(
                "❌ **Video nahi mili!**\n\n"
                "• Private / Age-Restricted video ho sakti hai\n"
                "• 2 min baad try karo"
            )

        await status.edit_text(
            f"🎬 **{stream['title']}**\n"
            f"📺 `{stream['quality']}`\n"
            f"📤 **Telegram pe bhej raha hoon...**"
        )

        start = time.time()

        # 🔥 MAGIC: Direct URL pass karo — Telegram khud download karega!
        await client.send_video(
            chat_id=message.chat.id,
            video=stream["url"],
            caption=(
                f"🎬 **{stream['title']}**\n\n"
                f"👤 `{stream['uploader']}`\n"
                f"📺 Quality: `{stream['quality']}`\n"
                f"⚡ **via Bot**"
            ),
            duration=stream.get("duration", 0),
            supports_streaming=True,
            reply_to_message_id=message.id,
            progress=progress,
            progress_args=("Uploading...", status, start),
        )

        await status.delete()
        print(f"✅ Video sent: {stream['title']}")

    except Exception as e:
        err = str(e)
        print("DL Error:", err)
        await status.edit_text(f"❌ **Error:** `{err[:400]}`")

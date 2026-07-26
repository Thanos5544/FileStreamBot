import os
import time
import math
import asyncio
import subprocess
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp

# ==========================================
# 🟢 STARTUP CHECK
# ==========================================
def startup_check():
    for name, cmd in [('Node.js', ['node', '--version']),
                       ('FFmpeg', ['ffmpeg', '-version']),
                       ('yt-dlp', ['yt-dlp', '--version'])]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            v = (r.stdout or r.stderr).strip().split('\n')[0]
            print(f"🟢 {name}: {v}")
        except Exception as e:
            print(f"❌ {name}: NOT FOUND ({e})")

    # Check EJS cache
    ejs_dir = "/root/.cache/yt-dlp/ytdlp-ejs"
    if os.path.exists(ejs_dir):
        files = os.listdir(ejs_dir)
        print(f"🟢 EJS Cache: {files}")
    else:
        print(f"❌ EJS Cache: NOT FOUND at {ejs_dir}")

startup_check()

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

# ==========================================
# 🍪 FIND COOKIES
# ==========================================
def find_cookies():
    for p in ["cookies.txt", "./cookies.txt", "../cookies.txt",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cookies.txt")]:
        if os.path.exists(p):
            print(f"✅ Cookies: {os.path.abspath(p)}")
            return p
    return None

# ==========================================
# 🚀 DOWNLOADER (EJS Cached + Cookies)
# ==========================================
def download_video(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    cookie_path = find_cookies()

    ydl_opts = {
        'format': 'bv*+ba/b',
        'merge_output_format': 'mp4',
        'outtmpl': f'{output_dir}/%(title).50s_%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'nocheckcertificate': True,
        # EJS scripts already cached from Docker build
        'remote_components': ['ejs:github'],
    }

    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    print(f"🔄 Downloading with Cached EJS + Cookies...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith('.mp4'):
            filename = filename.rsplit('.', 1)[0] + '.mp4'

    # Thumbnail
    thumb_path = None
    thumb_url = info.get('thumbnail')
    if thumb_url:
        try:
            thumb_path = f"{output_dir}/thumb_{int(time.time())}.jpg"
            r = requests.get(thumb_url, timeout=15)
            if r.status_code == 200:
                with open(thumb_path, 'wb') as f: f.write(r.content)
            else: thumb_path = None
        except Exception: thumb_path = None

    return {
        "title": info.get("title", "Video"),
        "duration": info.get("duration", 0),
        "filepath": filename,
        "thumb": thumb_path,
        "uploader": info.get("uploader", "Unknown"),
        "cookie_used": bool(cookie_path)
    }

# ==========================================
# 🤖 /dl COMMAND
# ==========================================
@Client.on_message(filters.command(["dl", "yt", "video"]) & (filters.private | filters.group))
async def yt_download_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ **Link do bhai!**\n`/dl https://youtu.be/xxx`")

    url = message.command[1].strip()
    status = await message.reply_text("🔎 **Video check kar raha hoon...**")
    data = None

    try:
        cf = find_cookies()
        await status.edit_text(f"🍪 Cookies: {'✅' if cf else '❌'} | ️ **Downloading (Cached EJS)...**")

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, download_video, url)

        if not data or not os.path.exists(data["filepath"]):
            return await status.edit_text("❌ **Download fail!**")

        filepath = data["filepath"]
        thumb = data.get("thumb")
        fsize = os.path.getsize(filepath)

        if fsize > 2000 * 1024 * 1024:
            os.remove(filepath)
            return await status.edit_text("❌ **2GB se badi file!**")

        await status.edit_text("📤 **Upload ho raha hai...**")
        start = time.time()

        caption = (f"🎬 **{data['title']}**\n\n👤 `{data['uploader']}`\n"
                   f"📦 `{humanbytes(fsize)}`\n🍪 `{'✅' if data['cookie_used'] else '❌'}`\n⚡ **via Bot**")

        await client.send_video(
            chat_id=message.chat.id, video=filepath, caption=caption,
            duration=data.get("duration", 0),
            thumb=thumb if thumb and os.path.exists(thumb) else None,
            supports_streaming=True, reply_to_message_id=message.id,
            progress=progress, progress_args=("Uploading...", status, start)
        )
        await status.delete()

    except Exception as e:
        err = str(e)
        print("DL Error:", err)
        if "Sign in to confirm" in err:
            await status.edit_text("❌ **Cookie Expire!** Naya upload karo.")
        else:
            await status.edit_text(f"❌ **Error:** `{err[:400]}`")
    finally:
        try:
            if data and os.path.exists(data.get("filepath", "")): os.remove(data["filepath"])
            if data and data.get("thumb") and os.path.exists(data["thumb"]): os.remove(data["thumb"])
        except Exception: pass

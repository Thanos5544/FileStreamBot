import os
import time
import math
import asyncio
import subprocess
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# ==========================================
# 🟢 BGUTIL SERVER AUTO-START
# ==========================================
BGUTIL_PROC = None

def start_bgutil_server():
    global BGUTIL_PROC
    try:
        r = requests.get('http://127.0.0.1:4416/ping', timeout=2)
        if r.status_code == 200:
            print("✅ bgutil server already running!")
            return True
    except Exception:
        pass

    print("🚀 Starting bgutil PO Token server (Deno)...")
    try:
        BGUTIL_PROC = subprocess.Popen(
            ['deno', 'run', '-A', 'src/main.ts'],
            cwd='/opt/bgutil/server',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for i in range(15):
            time.sleep(1)
            try:
                r = requests.get('http://127.0.0.1:4416/ping', timeout=2)
                if r.status_code == 200:
                    print(f"✅ bgutil server ready! ({i+1}s)")
                    return True
            except Exception:
                pass
            if BGUTIL_PROC.poll() is not None:
                print("❌ bgutil process died!")
                break
    except Exception as e:
        print(f"❌ bgutil start failed: {e}")
    
    BGUTIL_PROC = None
    return False

start_bgutil_server()

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
            return p
    return None

# ==========================================
# 🚀 CLI DOWNLOADER (EJS + PO Token + Cookies = ALL)
# ==========================================
def download_video(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    cookie_path = find_cookies()

    cmd = [
        'yt-dlp',
        '--verbose',
        '--remote-components', 'ejs:github',
        '--js-runtimes', 'nodejs',
        '-f', 'bv*+ba/b',
        '--merge-output-format', 'mp4',
        '-o', f'{output_dir}/%(title).50s_%(id)s.%(ext)s',
        '--no-playlist',
        '--no-progress',
        '--print', 'after_move:filepath=%(filepath)s',
        '--print', 'after_move:title=%(title)s',
        '--print', 'after_move:duration=%(duration)s',
        '--print', 'after_move:uploader=%(uploader)s',
        '--print', 'after_move:thumbnail=%(thumbnail)s',
    ]

    if cookie_path:
        cmd.extend(['--cookies', cookie_path])

    cmd.append(url)

    print(f"🔄 Downloading with EJS + PO Token + Cookies...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Debug output
    for line in (result.stdout + result.stderr).split('\n'):
        ll = line.lower()
        if any(k in ll for k in ['ejs', 'signature', 'challenge', 'pot', 'bgutil', 'format', 'error', 'download', 'cache']):
            print(f"  | {line}")

    if result.returncode != 0:
        raise Exception(result.stderr[-400:])

    info = {}
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if '=' in line and not line.startswith('http') and not line.startswith('[debug]'):
            key, _, val = line.partition('=')
            info[key.strip()] = val.strip()

    filepath = info.get('filepath', '')
    if not filepath or not os.path.exists(filepath):
        mp4s = [os.path.join(output_dir, f) for f in os.listdir(output_dir)
                if f.endswith(('.mp4', '.webm', '.mkv'))]
        if mp4s:
            filepath = max(mp4s, key=os.path.getctime)
        else:
            raise Exception("No video file found!")

    print(f"✅ Downloaded: {filepath} ({os.path.getsize(filepath)} bytes)")

    thumb_path = None
    thumb_url = info.get('thumbnail', '')
    if thumb_url and thumb_url.startswith('http'):
        try:
            thumb_path = f"{output_dir}/thumb_{int(time.time())}.jpg"
            r = requests.get(thumb_url, timeout=15)
            if r.status_code == 200:
                with open(thumb_path, 'wb') as f: f.write(r.content)
            else: thumb_path = None
        except Exception: thumb_path = None

    try: duration = int(float(info.get('duration', '0')))
    except Exception: duration = 0

    return {
        "title": info.get('title', 'Video'),
        "duration": duration,
        "filepath": filepath,
        "thumb": thumb_path,
        "uploader": info.get('uploader', 'Unknown'),
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
        server_ok = "✅" if BGUTIL_PROC and BGUTIL_PROC.poll() is None else "❌"
        await status.edit_text(f"🍪 {'✅' if cf else '❌'} |  {server_ok} | ⬇️ **Downloading (EJS+POT+Cookie)...**")

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
                   f"📦 `{humanbytes(fsize)}`\n⚡ **via Bot**")

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
            await status.edit_text(f"❌ **Error:**\n```\n{err[:500]}\n```")
    finally:
        try:
            if data and os.path.exists(data.get("filepath", "")): os.remove(data["filepath"])
            if data and data.get("thumb") and os.path.exists(data["thumb"]): os.remove(data["thumb"])
        except Exception: pass

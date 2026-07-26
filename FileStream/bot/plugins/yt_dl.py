import os
import time
import math
import asyncio
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# ==========================================
# 🛠️ HELPERS & PROGRESS BAR
# ==========================================
def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN.get(n, '') + 'B'

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2] if tmp else "0s"

async def progress_for_pyrogram(current, total, ud_type, message, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 4.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        progress = "[{0}{1}] \n**Progress**: {2}%\n".format(
            ''.join(["█" for _ in range(math.floor(percentage / 10))]),
            ''.join(["░" for _ in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2)
        )

        tmp = progress + "{0} of {1}\n**Speed**: {2}/s\n**ETA**: {3}\n".format(
            humanbytes(current), humanbytes(total), humanbytes(speed),
            time_formatter(estimated_total_time) if time_formatter(estimated_total_time) != '' else "0 s"
        )
        try:
            await message.edit_text(f"⏳ **{ud_type}**\n\n{tmp}")
        except Exception:
            pass

# ==========================================
# 🍪 FIND COOKIES FILE
# ==========================================
def find_cookies():
    possible_paths = [
        "cookies.txt",
        "./cookies.txt",
        "../cookies.txt",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cookies.txt"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            print(f"✅ Cookies found at: {os.path.abspath(p)}")
            return p
    print("⚠️ cookies.txt NOT found anywhere!")
    return None

# ==========================================
# 🚀 BULLETPROOF DOWNLOADER (5-CLIENT RETRY)
# ==========================================
def download_with_cookies(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    cookie_path = find_cookies()

    # 5 alag client configs — ek fail toh doosra try
    configs = [
        # 1. WEB client + cookies (sabse reliable)
        {
            'format': 'bv*+ba/b',
            'merge_output_format': 'mp4',
            'extractor_args': {'youtube': {'player_client': ['web']}},
        },
        # 2. TV Embedded (no cookies needed, bot detection bypass)
        {
            'format': 'bv*+ba/b',
            'merge_output_format': 'mp4',
            'extractor_args': {'youtube': {'player_client': ['tv_embedded']}},
        },
        # 3. iOS client
        {
            'format': 'bv*+ba/b',
            'merge_output_format': 'mp4',
            'extractor_args': {'youtube': {'player_client': ['ios']}},
        },
        # 4. Default (yt-dlp khud decide kare)
        {
            'format': 'bv*+ba/b',
            'merge_output_format': 'mp4',
        },
        # 5. Last resort — single stream, no merge
        {
            'format': 'b',
        },
    ]

    base_opts = {
        'outtmpl': f'{output_dir}/%(title).50s_%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    if cookie_path:
        base_opts['cookiefile'] = cookie_path

    info = None
    filename = None
    last_error = None

    for i, cfg in enumerate(configs):
        try:
            client_name = cfg.get('extractor_args', {}).get('youtube', {}).get('player_client', ['default'])[0]
            print(f"🔄 Try {i+1}/5 — Client: {client_name} | Format: {cfg['format']}")
            opts = {**base_opts, **cfg}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if cfg.get('merge_output_format') and not filename.endswith('.mp4'):
                    filename = filename.rsplit('.', 1)[0] + '.mp4'
                print(f"✅ SUCCESS with client: {client_name}")
                break
        except Exception as e:
            last_error = str(e)
            print(f"❌ Try {i+1} failed: {last_error[:120]}")
            continue

    if not info or not filename or not os.path.exists(filename):
        # Debug: available formats print karo
        try:
            with yt_dlp.YoutubeDL({'quiet': False, 'listformats': True, 'cookiefile': cookie_path} if cookie_path else {'quiet': False, 'listformats': True}) as ydl:
                ydl.extract_info(url, download=False)
        except Exception as dbg:
            print(f"DEBUG formats: {dbg}")
        raise Exception(f"All 5 clients failed! Last: {last_error}")

    # Thumbnail
    thumb_path = None
    thumb_url = info.get('thumbnail')
    if thumb_url:
        try:
            thumb_path = f"{output_dir}/thumb_{info.get('id', 'pic')}.jpg"
            r = requests.get(thumb_url, timeout=15)
            if r.status_code == 200:
                with open(thumb_path, 'wb') as f:
                    f.write(r.content)
            else:
                thumb_path = None
        except Exception:
            thumb_path = None

    return {
        "title": info.get("title", "Video"),
        "duration": info.get("duration", 0),
        "filepath": filename,
        "thumb": thumb_path,
        "uploader": info.get("uploader", "Unknown"),
        "cookie_used": bool(cookie_path)
    }

# ==========================================
# 🤖 /dl or /yt COMMAND
# ==========================================
@Client.on_message(filters.command(["dl", "yt", "video"]) & (filters.private | filters.group))
async def yt_download_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **Link toh do bhai!**\n\n"
            "**Example:** `/dl https://youtu.be/xxxxxx`"
        )

    url = message.command[1].strip()
    status = await message.reply_text("🔎 **Video check kar raha hoon...**")

    data = None
    try:
        cookie_file = find_cookies()
        if cookie_file:
            await status.edit_text("🍪 **Cookies Active! Downloading Video...**")
        else:
            await status.edit_text("⚠️ **No Cookies! Trying without auth...**")

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, download_with_cookies, url)

        if not data or not os.path.exists(data["filepath"]):
            return await status.edit_text("❌ **Download fail ho gaya!**")

        filepath = data["filepath"]
        thumb = data.get("thumb")
        file_size = os.path.getsize(filepath)

        if file_size > 2000 * 1024 * 1024:
            os.remove(filepath)
            if thumb and os.path.exists(thumb):
                os.remove(thumb)
            return await status.edit_text("❌ **File 2GB se badi hai!**")

        await status.edit_text("📤 **Telegram pe upload ho raha hai...**")
        start_time = time.time()

        cookie_status = "✅ Active" if data["cookie_used"] else "⚠️ Not Found"
        caption = (
            f"🎬 **{data['title']}**\n\n"
            f"👤 **Uploader:** `{data['uploader']}`\n"
            f"📦 **Size:** `{humanbytes(file_size)}`\n"
            f"🍪 **Cookies:** `{cookie_status}`\n"
            f"⚡ **Downloaded via Bot**"
        )

        await client.send_video(
            chat_id=message.chat.id,
            video=filepath,
            caption=caption,
            duration=data.get("duration", 0),
            thumb=thumb if thumb and os.path.exists(thumb) else None,
            supports_streaming=True,
            reply_to_message_id=message.id,
            progress=progress_for_pyrogram,
            progress_args=("Uploading Video...", status, start_time)
        )
        await status.delete()

    except Exception as e:
        err_msg = str(e)
        print("DL Error:", err_msg)
        if "Sign in to confirm" in err_msg:
            await status.edit_text(
                "❌ **Cookie Expire!** Naya `cookies.txt` upload karo."
            )
        else:
            await status.edit_text(f"❌ **Error:** `{err_msg[:400]}`")

    finally:
        try:
            if data and os.path.exists(data.get("filepath", "")):
                os.remove(data["filepath"])
            if data and data.get("thumb") and os.path.exists(data["thumb"]):
                os.remove(data["thumb"])
        except Exception:
            pass

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
    print("⚠️ cookies.txt NOT found!")
    return None

# ==========================================
# 🚀 DOWNLOADER (Node.js + FFmpeg + Cookies = 1000%)
# ==========================================
def download_video(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    cookie_path = find_cookies()

    ydl_opts = {
        'format': 'bv*+ba/b',
        'merge_output_format': 'mp4',
        'outtmpl': f'{output_dir}/%(title).50s_%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
    }

    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    print(f"🔄 Downloading... Cookies={bool(cookie_path)}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith('.mp4'):
            filename = filename.rsplit('.', 1)[0] + '.mp4'

    # Thumbnail download
    thumb_path = None
    thumb_url = info.get('thumbnail')
    if thumb_url:
        try:
            thumb_path = f"{output_dir}/thumb_{int(time.time())}.jpg"
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
            await status.edit_text("⬇️ **Downloading Video...**")

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, download_video, url)

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
            await status.edit_text("❌ **Cookie Expire!** Naya `cookies.txt` upload karo.")
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

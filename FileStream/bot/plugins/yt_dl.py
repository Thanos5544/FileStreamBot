import os
import time
import math
import asyncio
import aiohttp
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# ==========================================
# 🛠️ HELPERS & PROGRESS BAR
# ==========================================
def humanbytes(size):
    if not size: return ""
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
# 🚀 METHOD 1: COBALT API (NO COOKIES/NO IP BAN)
# ==========================================
async def download_via_api(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    data = {"url": url, "videoQuality": "720", "filenameStyle": "basic"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=data, headers=headers) as resp:
            if resp.status != 200: return None
            res = await resp.json()
            
            direct_url = res.get("url")
            if not direct_url: return None
            
            # Download Video File
            filename = f"{output_dir}/video_{int(time.time())}.mp4"
            async with session.get(direct_url) as file_resp:
                with open(filename, "wb") as f:
                    while True:
                        chunk = await file_resp.content.read(1024 * 1024)
                        if not chunk: break
                        f.write(chunk)
            return {"filepath": filename, "title": "YouTube Video", "duration": 0, "thumb": None, "uploader": "YouTube"}

# ==========================================
# 🚀 METHOD 2: YT-DLP ANDROID CLIENT BYPASS
# ==========================================
def download_via_ytdlp_bypass(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    
    # Ye Android & iOS client use karta hai jispe YouTube IP block ya Cookie nahi maangta
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{output_dir}/%(title).50s_%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'writethumbnail': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web_embedded'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        thumb_file = filename.rsplit('.', 1)[0] + ".webp"
        if not os.path.exists(thumb_file):
            thumb_file = filename.rsplit('.', 1)[0] + ".jpg"
            if not os.path.exists(thumb_file): thumb_file = None
            
        return {
            "title": info.get("title", "Video"),
            "duration": info.get("duration", 0),
            "filepath": filename,
            "thumb": thumb_file,
            "uploader": info.get("uploader", "Unknown")
        }

# ==========================================
# 🤖 /dl or /yt COMMAND
# ==========================================
@Client.on_message(filters.command(["dl", "yt", "video"]) & (filters.private | filters.group))
async def yt_download_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ **Link toh do bhai!**\n\n**Example:** `/dl https://youtu.be/xxxxxx`")
    
    url = message.command[1]
    status = await message.reply_text("🔎 **Video find kar raha hoon...**")
    
    data = None
    try:
        # PEHLE: Bina Cookie waala Android Bypass try karega
        await status.edit_text("⬇️ **Downloading Video (Fast Mode)...**")
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, download_via_ytdlp_bypass, url)
        except Exception as e:
            print(f"YT-DLP Bypass Failed: {e}. Switching to API...")
            
        # AGAR IP BAN HAI TOH: Direct Server API use karega (100% Working Backup)
        if not data or not os.path.exists(data.get("filepath", "")):
            await status.edit_text("⚡ **Server IP Blocked by YT. Using Bypass API...**")
            data = await download_via_api(url)
            
        if not data or not os.path.exists(data["filepath"]):
            return await status.edit_text("❌ **Download fail ho gaya!** Link private ya broken ho sakta hai.")
            
        filepath = data["filepath"]
        thumb = data.get("thumb")
        file_size = os.path.getsize(filepath)

        if file_size > 2000 * 1024 * 1024:
            os.remove(filepath)
            return await status.edit_text("❌ **File 2GB se badi hai! Telegram allow nahi karta.**")

        await status.edit_text("📤 **Telegram pe upload ho raha hai...**")
        start_time = time.time()
        
        caption = (
            f"🎬 **{data['title']}**\n\n"
            f"👤 **Uploader:** `{data['uploader']}`\n"
            f"📦 **Size:** `{humanbytes(file_size)}`\n"
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
        await status.edit_text(f"❌ **Error:** `{str(e)[:250]}`")
        
    finally:
        # 🧹 Server Cleanup (Storage full nahi hoga)
        try:
            if data and os.path.exists(data.get("filepath", "")):
                os.remove(data["filepath"])
            if data and data.get("thumb") and os.path.exists(data["thumb"]):
                os.remove(data["thumb"])
        except Exception:
            pass

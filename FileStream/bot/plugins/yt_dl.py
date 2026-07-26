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
# 🚀 ULTRA-FAST DOWNLOADER (NO FFMPEG NEEDED)
# ==========================================
def download_video_direct(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    
    # 'best[ext=mp4]' download karta hai wo video jisme AUDIO aur VIDEO pehle se mix ho.
    # Isse FFmpeg ki zaroorat nahi padti aur error kabhi nahi aata!
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': f'{output_dir}/%(title).50s_%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        # Ye YouTube ko bolta hai ki hum iPhone/Android app se dekh rahe hain (No Cookie Error)
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb', 'tvembedded'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        # Download Thumbnail directly via HTTP without using FFmpeg
        thumb_path = None
        thumb_url = info.get('thumbnail')
        if thumb_url:
            try:
                thumb_path = f"{output_dir}/thumb_{info.get('id', 'pic')}.jpg"
                r = requests.get(thumb_url, timeout=10)
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
            "uploader": info.get("uploader", "Unknown")
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
    status = await message.reply_text("🔎 **Video find kar raha hoon...**")
    
    data = None
    try:
        await status.edit_text("⬇️ **Downloading Video (Fast & Safe Mode)...**")
        
        # Background me download taaki bot hang na ho
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, download_video_direct, url)
            
        if not data or not os.path.exists(data["filepath"]):
            return await status.edit_text("❌ **Download fail ho gaya!** File save nahi ho payi.")
            
        filepath = data["filepath"]
        thumb = data.get("thumb")
        file_size = os.path.getsize(filepath)

        # Telegram Bot 2GB Limit Check
        if file_size > 2000 * 1024 * 1024:
            os.remove(filepath)
            if thumb and os.path.exists(thumb): os.remove(thumb)
            return await status.edit_text("❌ **File 2GB se badi hai! Telegram bot allow nahi karta.**")

        await status.edit_text("📤 **Telegram pe upload ho raha hai...**")
        start_time = time.time()
        
        caption = (
            f"🎬 **{data['title']}**\n\n"
            f"👤 **Uploader:** `{data['uploader']}`\n"
            f"📦 **Size:** `{humanbytes(file_size)}`\n"
            f"⚡ **Downloaded via Bot**"
        )

        # Video Send karna
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
        # Ab agar koi error aayega toh bot CHAT ME EXACT ERROR BATEYEGA taaki hume pata chale
        err_msg = str(e)
        print("DL Error:", err_msg)
        await status.edit_text(
            f"❌ **Download Failed!**\n\n"
            f"**Reason:** `{err_msg[:350]}`\n\n"
            f"*Note: Agar age-restricted ya private video hai toh nahi hogi.*"
        )
        
    finally:
        # 🧹 Server Cleanup (Storage full nahi hoga)
        try:
            if data and os.path.exists(data.get("filepath", "")):
                os.remove(data["filepath"])
            if data and data.get("thumb") and os.path.exists(data["thumb"]):
                os.remove(data["thumb"])
        except Exception:
            pass

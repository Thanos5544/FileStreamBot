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
# 🌐 EXTERNAL WEB APIs (Y2Mate / Cobalt Style)
# Ye server IP ban ko 100% bypass karte hain!
# ==========================================
async def get_video_via_external_api(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    direct_mp4_url = None
    title = "YouTube Video"
    
    async with aiohttp.ClientSession() as session:
        # --- API 1: Cobalt Tools API (Best Open Source Downloader) ---
        try:
            api_url = "https://api.cobalt.tools/"
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            async with session.post(api_url, json={"url": url, "videoQuality": "720"}, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    direct_mp4_url = res.get("url")
        except Exception as e:
            print("API 1 (Cobalt) Failed:", e)

        # --- API 2: VKR Worker API (Y2Mate Alternative) ---
        if not direct_mp4_url:
            try:
                vkr_url = f"https://api.vkrdownloader.workers.dev/server?v={url}"
                async with session.get(vkr_url, timeout=15) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        title = res.get("title", title)
                        # Find 720p or 480p mp4 link
                        for fmt in res.get("formats", []):
                            if fmt.get("ext") == "mp4" and fmt.get("url"):
                                direct_mp4_url = fmt["url"]
                                break
            except Exception as e:
                print("API 2 (VKR) Failed:", e)

        # --- API 3: TiklyDown / Universal Downloader API ---
        if not direct_mp4_url:
            try:
                td_url = f"https://api.tiklydown.eu.org/api/download?url={url}"
                async with session.get(td_url, timeout=15) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        title = res.get("title", title)
                        direct_mp4_url = res.get("video", {}).get("url") or res.get("url")
            except Exception as e:
                print("API 3 (TiklyDown) Failed:", e)

        # Agar kisi bhi API ne direct MP4 link de diya, toh usko download kar lo
        if direct_mp4_url:
            filename = f"{output_dir}/video_{int(time.time())}.mp4"
            async with session.get(direct_mp4_url) as file_resp:
                if file_resp.status == 200:
                    with open(filename, "wb") as f:
                        while True:
                            chunk = await file_resp.content.read(1024 * 1024) # 1MB Chunk
                            if not chunk: break
                            f.write(chunk)
                    return {"filepath": filename, "title": title, "duration": 0, "thumb": None, "uploader": "Web API Bypass"}
    return None

# ==========================================
# 🛡️ METHOD 2: YT-DLP TV-EMBEDDED BYPASS
# Agar Web APIs slow hon toh ye TV Client use karega
# ==========================================
def download_via_tvembedded(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': f'{output_dir}/%(title).50s_%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        # Ye YouTube ko bolta hai ki hum Smart TV se video dekh rahe hain (No Cookie Error on Server IPs)
        'extractor_args': {
            'youtube': {
                'player_client': ['tvembedded', 'android_vr'],
                'skip': ['hls', 'dash']
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return {
            "title": info.get("title", "Video"),
            "duration": info.get("duration", 0),
            "filepath": filename,
            "thumb": None,
            "uploader": info.get("uploader", "Unknown")
        }

# ==========================================
# 🤖 /dl or /yt COMMAND
# ==========================================
@Client.on_message(filters.command(["dl", "yt", "video"]) & (filters.private | filters.group))
async def yt_download_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ **Link toh do bhai!**\n\n**Example:** `/dl https://youtu.be/xxxxxx`")
    
    url = message.command[1].strip()
    status = await message.reply_text("🔎 **Video find kar raha hoon...**")
    
    data = None
    try:
        # PEHLE: External Web APIs (Y2Mate / Cobalt Bypass) se try karega taaki IP block ka error na aaye
        await status.edit_text("⚡ **Bypassing Server Ban via External Web API...**")
        data = await get_video_via_external_api(url)
            
        # AGAR WEB API BUSY HAI: Toh Smart TV Client Bypass use karega
        if not data or not os.path.exists(data.get("filepath", "")):
            await status.edit_text("⬇️ **Web API Busy! Using Smart-TV Client Bypass...**")
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, download_via_tvembedded, url)
            
        if not data or not os.path.exists(data["filepath"]):
            return await status.edit_text("❌ **Download fail ho gaya!** Link private ya broken ho sakta hai.")
            
        filepath = data["filepath"]
        file_size = os.path.getsize(filepath)

        # Telegram Bot 2GB Limit Check
        if file_size > 2000 * 1024 * 1024:
            os.remove(filepath)
            return await status.edit_text("❌ **File 2GB se badi hai! Telegram bot allow nahi karta.**")

        await status.edit_text("📤 **Telegram pe upload ho raha hai...**")
        start_time = time.time()
        
        caption = (
            f"🎬 **{data['title']}**\n\n"
            f"👤 **Uploader:** `{data['uploader']}`\n"
            f"📦 **Size:** `{humanbytes(file_size)}`\n"
            f"⚡ **Downloaded via Multi-API Bot**"
        )

        # Video Send karna
        await client.send_video(
            chat_id=message.chat.id,
            video=filepath,
            caption=caption,
            duration=data.get("duration", 0),
            supports_streaming=True,
            reply_to_message_id=message.id,
            progress=progress_for_pyrogram,
            progress_args=("Uploading Video...", status, start_time)
        )
        await status.delete()

    except Exception as e:
        err_msg = str(e)
        print("DL Error:", err_msg)
        await status.edit_text(
            f"❌ **Download Failed!**\n\n"
            f"**Reason:** `{err_msg[:300]}`\n\n"
            f"*Note: Agar video age-restricted ya private hai toh nahi hogi.*"
        )
        
    finally:
        # 🧹 Server Cleanup (Storage full nahi hoga)
        try:
            if data and os.path.exists(data.get("filepath", "")):
                os.remove(data["filepath"])
        except Exception:
            pass

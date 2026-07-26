import os
import time
import math
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

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
# 🌐 4x MULTI-SERVER API BYPASS ENGINE
# Ye YouTube IP ban aur Cookie error ko 100% bypass karta hai
# ==========================================
async def get_video_from_apis(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    
    # 4 Alag-alag API servers (Agar 1 fail ho toh agla try hoga)
    api_servers = [
        "https://api.cobalt.tools/",
        "https://cobalt.qreere.com/",
        "https://cobalt.kino.su/",
    ]
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    direct_mp4_url = None
    title = f"Video_{int(time.time())}"

    async with aiohttp.ClientSession() as session:
        # --- METHOD 1: Try Cobalt Instances (100% Ad-free & High Speed) ---
        for server in api_servers:
            try:
                payload = {"url": url, "videoQuality": "720"}
                async with session.post(server, json=payload, headers=headers, timeout=12) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        direct_mp4_url = res.get("url")
                        if direct_mp4_url:
                            break
            except Exception as e:
                continue

        # --- METHOD 2: Try Universal TiklyDown API (Backup) ---
        if not direct_mp4_url:
            try:
                td_url = f"https://api.tiklydown.eu.org/api/download?url={url}"
                async with session.get(td_url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        title = res.get("title", title)
                        direct_mp4_url = res.get("video", {}).get("url") or res.get("url")
            except Exception:
                pass

        # --- DOWNLOAD FILE TO SERVER ---
        if direct_mp4_url:
            filename = f"{output_dir}/{title[:40].replace(' ', '_')}_{int(time.time())}.mp4"
            async with session.get(direct_mp4_url, headers=headers, timeout=600) as file_resp:
                if file_resp.status == 200:
                    with open(filename, "wb") as f:
                        while True:
                            chunk = await file_resp.content.read(1024 * 1024) # 1MB Chunk
                            if not chunk:
                                break
                            f.write(chunk)
                    return {
                        "filepath": filename,
                        "title": title,
                        "uploader": "YouTube / Insta"
                    }
    return None

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
    status = await message.reply_text("🔎 **API Server se Video fetch kar raha hoon...**")
    
    data = None
    try:
        await status.edit_text("⬇️ **Downloading Video (Bypassing Server Ban)...**")
        
        # 4 API servers se direct MP4 file pull karega
        data = await get_video_from_apis(url)
            
        if not data or not os.path.exists(data.get("filepath", "")):
            return await status.edit_text(
                "❌ **Download fail ho gaya!**\n\n"
                "• Ho sakta hai video Private ya Age-Restricted ho.\n"
                "• Ya phir link invalid hai."
            )
            
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
            f"📦 **Size:** `{humanbytes(file_size)}`\n"
            f"⚡ **Downloaded via Bot**"
        )

        # Video Send karna
        await client.send_video(
            chat_id=message.chat.id,
            video=filepath,
            caption=caption,
            supports_streaming=True,
            reply_to_message_id=message.id,
            progress=progress_for_pyrogram,
            progress_args=("Uploading Video...", status, start_time)
        )
        await status.delete()

    except Exception as e:
        err_msg = str(e)
        print("DL Error:", err_msg)
        await status.edit_text(f"❌ **Error:** `{err_msg[:300]}`")
        
    finally:
        # 🧹 Server Cleanup (Storage full nahi hoga)
        try:
            if data and os.path.exists(data.get("filepath", "")):
                os.remove(data["filepath"])
        except Exception:
            pass

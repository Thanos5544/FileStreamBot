import os
import time
import asyncio
import yt_dlp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

COOKIES_FILE = "cookies.txt"
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def human_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


async def edit_progress(msg, text, last):
    """Rate-limit edits to avoid flood"""
    now = time.time()
    if now - last[0] >= 3:
        last[0] = now
        try:
            await msg.edit_text(text)
        except:
            pass


@Client.on_message(filters.command("ytdl"))
async def ytdl_handler(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "📥 <b>YouTube Downloader</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/ytdl https://youtu.be/xxxx</code>"
        )

    url = message.command[1]
    status = await message.reply_text("🔍 <b>Fetching info...</b>")

    last_edit = [0]
    loop = asyncio.get_event_loop()

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            if total:
                pct = done * 100 / total
                bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                txt = (
                    f"📥 <b>Downloading...</b>\n\n"
                    f"<code>{bar}</code> {pct:.1f}%\n"
                    f"📦 {human_size(done)} / {human_size(total)}\n"
                    f"🚀 {human_size(speed)}/s"
                )
                asyncio.run_coroutine_threadsafe(
                    edit_progress(status, txt, last_edit), loop
                )

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title).50s.%(ext)s"),
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    file_path = None
    try:
        def do_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info

        file_path, info = await loop.run_in_executor(None, do_download)

        # Agar merge/convert hua to extension mp4 ho sakti hai
        if not os.path.exists(file_path):
            base = os.path.splitext(file_path)[0]
            for ext in [".mp4", ".mkv", ".webm"]:
                if os.path.exists(base + ext):
                    file_path = base + ext
                    break

        title = info.get("title", "Video")
        duration = info.get("duration", 0)
        size = os.path.getsize(file_path)

        if size > 2 * 1024 * 1024 * 1024:  # 2GB limit
            await status.edit_text("❌ <b>File 2GB se badi hai, upload nahi ho sakti.</b>")
            return

        await status.edit_text("📤 <b>Uploading...</b>")

        await client.send_video(
            chat_id=message.chat.id,
            video=file_path,
            caption=f"<b>{title}</b>\n\n📦 {human_size(size)}",
            duration=duration,
            reply_to_message_id=message.id,
            parse_mode=ParseMode.HTML,
        )

        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ <b>Error</b>\n\n<code>{str(e)[:400]}</code>")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

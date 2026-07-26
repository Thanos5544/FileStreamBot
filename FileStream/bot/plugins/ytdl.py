import os
import time
import uuid
import asyncio
import yt_dlp
from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

COOKIES_FILE = "cookies.txt"
DOWNLOAD_DIR = "downloads"
MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YT_CACHE = {}


def cb_starts(prefix):
    return filters.create(lambda _, __, q: bool(q.data and q.data.startswith(prefix)))


def human_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def human_time(sec):
    if not sec:
        return "N/A"
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def cleanup_cache():
    now = time.time()
    for t in list(YT_CACHE.keys()):
        if now - YT_CACHE[t].get("time", now) > 1800:
            YT_CACHE.pop(t, None)


def base_opts():
    opts = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


async def edit_safe(msg, text, last):
    now = time.time()
    if now - last[0] >= 3:
        last[0] = now
        try:
            await msg.edit_text(text)
        except:
            pass


@Client.on_message(filters.command("ytdl"))
async def ytdl_handler(client, message):
    cleanup_cache()

    if len(message.command) < 2:
        return await message.reply_text(
            "📥 <b>YouTube Downloader</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/ytdl https://youtu.be/xxxx</code>",
            parse_mode=ParseMode.HTML,
        )

    url = message.command[1]
    status = await message.reply_text("🔍 <b>Fetching info...</b>", parse_mode=ParseMode.HTML)

    loop = asyncio.get_event_loop()

    def get_info():
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await loop.run_in_executor(None, get_info)
    except Exception as e:
        return await status.edit_text(
            f"❌ <b>Error</b>\n\n<code>{str(e)[:400]}</code>",
            parse_mode=ParseMode.HTML,
        )

    title = info.get("title", "Video")
    duration = info.get("duration", 0)
    uploader = info.get("uploader", "Unknown")

    token = uuid.uuid4().hex[:10]
    YT_CACHE[token] = {
        "url": url,
        "title": title,
        "duration": duration,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "reply_to": message.id,
        "time": time.time(),
    }

    buttons = [
        [
            InlineKeyboardButton("360p", callback_data=f"yt|{token}|360"),
            InlineKeyboardButton("480p", callback_data=f"yt|{token}|480"),
        ],
        [
            InlineKeyboardButton("720p", callback_data=f"yt|{token}|720"),
            InlineKeyboardButton("1080p", callback_data=f"yt|{token}|1080"),
        ],
        [
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"yt|{token}|audio"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data=f"yt|{token}|cancel"),
        ],
    ]

    await status.edit_text(
        f"<b>{title}</b>\n\n"
        f"👤 <b>Channel:</b> {uploader}\n"
        f"⏱ <b>Duration:</b> {human_time(duration)}\n\n"
        f"<b>Select quality:</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML,
    )


@Client.on_callback_query(cb_starts("yt|"))
async def yt_cb(client, query):
    try:
        _, token, choice = query.data.split("|")
        data = YT_CACHE.get(token)

        if not data:
            return await query.answer("Expired!", show_alert=True)
        if query.from_user.id != data["user_id"]:
            return await query.answer("Not for you!", show_alert=True)

        if choice == "cancel":
            YT_CACHE.pop(token, None)
            await query.answer("Cancelled")
            await query.message.delete()
            raise StopPropagation

        await query.answer("Starting...")

        url = data["url"]
        title = data["title"]
        duration = data["duration"]
        status = query.message

        last_edit = [0]
        loop = asyncio.get_event_loop()

        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes", 0)
                speed = d.get("speed") or 0
                if total:
                    pct = done * 100 / total
                    filled = int(pct / 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    txt = (
                        f"📥 <b>Downloading...</b>\n\n"
                        f"<code>{bar}</code> {pct:.1f}%\n"
                        f"📦 {human_size(done)} / {human_size(total)}\n"
                        f"🚀 {human_size(speed)}/s"
                    )
                    asyncio.run_coroutine_threadsafe(
                        edit_safe(status, txt, last_edit), loop
                    )

        opts = base_opts()
        opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{token}_%(title).40s.%(ext)s")
        opts["progress_hooks"] = [progress_hook]

        is_audio = choice == "audio"

        if is_audio:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            q = int(choice)
            opts["format"] = (
                f"bestvideo[height<={q}][ext=mp4]+bestaudio[ext=m4a]/"
                f"best[height<={q}][ext=mp4]/best[height<={q}]/best"
            )
            opts["merge_output_format"] = "mp4"

        await status.edit_text("📥 <b>Downloading...</b>", parse_mode=ParseMode.HTML)

        file_path = None

        def do_download():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                fp = ydl.prepare_filename(info)
                if is_audio:
                    fp = os.path.splitext(fp)[0] + ".mp3"
                return fp, info

        file_path, info = await loop.run_in_executor(None, do_download)

        # File dhundo agar extension change hui ho
        if not os.path.exists(file_path):
            base = os.path.splitext(file_path)[0]
            for ext in [".mp4", ".mkv", ".webm", ".mp3", ".m4a"]:
                if os.path.exists(base + ext):
                    file_path = base + ext
                    break

        if not file_path or not os.path.exists(file_path):
            YT_CACHE.pop(token, None)
            return await status.edit_text("❌ <b>Download failed</b>", parse_mode=ParseMode.HTML)

        size = os.path.getsize(file_path)

        if size > MAX_SIZE:
            os.remove(file_path)
            YT_CACHE.pop(token, None)
            return await status.edit_text(
                "❌ <b>File 2GB se badi hai, upload nahi ho sakti.</b>",
                parse_mode=ParseMode.HTML,
            )

        await status.edit_text("📤 <b>Uploading...</b>", parse_mode=ParseMode.HTML)

        caption = f"<b>{title}</b>\n\n📦 {human_size(size)}"

        if is_audio:
            await client.send_audio(
                chat_id=data["chat_id"],
                audio=file_path,
                caption=caption,
                title=title,
                duration=duration,
                reply_to_message_id=data["reply_to"],
                parse_mode=ParseMode.HTML,
            )
        else:
            await client.send_video(
                chat_id=data["chat_id"],
                video=file_path,
                caption=caption,
                duration=duration,
                reply_to_message_id=data["reply_to"],
                parse_mode=ParseMode.HTML,
            )

        await status.delete()

        if os.path.exists(file_path):
            os.remove(file_path)

        YT_CACHE.pop(token, None)

    except StopPropagation:
        raise
    except Exception as e:
        try:
            await query.message.edit_text(
                f"❌ <b>Error</b>\n\n<code>{str(e)[:400]}</code>",
                parse_mode=ParseMode.HTML,
            )
        except:
            pass
    finally:
        raise StopPropagation

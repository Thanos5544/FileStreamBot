import os
import re
import time
import uuid
import shutil
import asyncio
from pathlib import Path

import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


DOWNLOAD_DIR = "downloads/youtube"

# Buttons me ye qualities aayengi
QUALITIES = [144, 240, 360, 480, 720]

# Temporary memory storage for links
YT_CACHE = {}

YOUTUBE_REGEX = re.compile(
    r"(https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be)/\S+)",
    re.IGNORECASE
)


def get_youtube_url(text: str):
    if not text:
        return None

    match = YOUTUBE_REGEX.search(text)
    if match:
        return match.group(1)

    return None


def cleanup_cache():
    now = time.time()
    expired = []

    for token, data in YT_CACHE.items():
        if now - data.get("time", now) > 1800:  # 30 min
            expired.append(token)

    for token in expired:
        YT_CACHE.pop(token, None)


def make_quality_buttons(token: str):
    buttons = []

    row = []
    for q in QUALITIES:
        row.append(
            InlineKeyboardButton(
                text=f"{q}p",
                callback_data=f"ytdl|{token}|{q}"
            )
        )

        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data=f"ytdl_cancel|{token}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def base_ytdl_opts():
    """
    Cookies use nahi kar raha.
    Ye options cookies issue kam karne ke liye hain, but 100% guarantee nahi.
    """
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "restrictfilenames": True,
        "geo_bypass": True,
        "cachedir": False,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"]
            }
        },
    }


def get_video_info(url: str):
    opts = base_ytdl_opts()
    opts.update({
        "skip_download": True,
    })

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "YouTube Video")
    duration = info.get("duration")
    uploader = info.get("uploader")

    return {
        "title": title,
        "duration": duration,
        "uploader": uploader
    }


def seconds_to_time(seconds):
    if not seconds:
        return "Unknown"

    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h:
        return f"{h}:{m:02d}:{s:02d}"

    return f"{m}:{s:02d}"


def find_downloaded_file(folder: str):
    if not os.path.exists(folder):
        return None

    files = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            files.append(path)

    if not files:
        return None

    # Biggest file usually final video hoti hai
    files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    return files[0]


def download_youtube_video(url: str, quality: int, token: str):
    folder = os.path.join(DOWNLOAD_DIR, token)
    Path(folder).mkdir(parents=True, exist_ok=True)

    ffmpeg_ok = shutil.which("ffmpeg") is not None

    if ffmpeg_ok:
        # Best video + audio merge karega
        fmt = (
            f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={quality}]+bestaudio/"
            f"best[height<={quality}][ext=mp4]/"
            f"best[height<={quality}]/best"
        )
    else:
        # Agar ffmpeg nahi hai to progressive mp4 download karega
        # Usually 360p/480p safe hoti hai
        fmt = (
            f"best[height<={quality}][ext=mp4]/"
            f"best[height<={quality}]/best"
        )

    opts = base_ytdl_opts()
    opts.update({
        "format": fmt,
        "outtmpl": f"{folder}/%(title).70s-%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "postprocessor_args": ["-movflags", "+faststart"],
    })

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "YouTube Video")

    filepath = find_downloaded_file(folder)

    return filepath, title, ffmpeg_ok


@Client.on_message(filters.command(["yt", "ytdl"]) & filters.private)
async def yt_start_handler(client: Client, message: Message):
    cleanup_cache()

    text = message.text or message.caption or ""
    url = get_youtube_url(text)

    if not url and message.reply_to_message:
        reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        url = get_youtube_url(reply_text)

    if not url:
        return await message.reply_text(
            "YouTube link bhejo bro.\n\n"
            "Example:\n"
            "`/yt https://youtu.be/VIDEO_ID`"
        )

    msg = await message.reply_text("🔎 Video info fetch kar raha hu...")

    try:
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, get_video_info, url)

        token = uuid.uuid4().hex[:10]

        YT_CACHE[token] = {
            "url": url,
            "user_id": message.from_user.id,
            "title": info.get("title", "YouTube Video"),
            "time": time.time()
        }

        title = info.get("title", "YouTube Video")
        uploader = info.get("uploader") or "Unknown"
        duration = seconds_to_time(info.get("duration"))

        await msg.edit_text(
            f"🎬 Title: {title}\n"
            f"👤 Channel: {uploader}\n"
            f"⏱ Duration: {duration}\n\n"
            f"Quality select karo:",
            reply_markup=make_quality_buttons(token)
        )

    except Exception as e:
        await msg.edit_text(
            "❌ Video info fetch nahi hua.\n\n"
            f"Error:\n`{str(e)[:900]}`"
        )


@Client.on_callback_query(filters.regex(r"^ytdl\|"))
async def yt_quality_callback(client: Client, query: CallbackQuery):
    cleanup_cache()

    try:
        _, token, quality = query.data.split("|")
        quality = int(quality)
    except Exception:
        return await query.answer("Invalid button.", show_alert=True)

    data = YT_CACHE.get(token)

    if not data:
        return await query.answer(
            "Link expired ho gaya. Dobara /yt command bhejo.",
            show_alert=True
        )

    if query.from_user.id != data["user_id"]:
        return await query.answer(
            "Ye button tumhare liye nahi hai bro.",
            show_alert=True
        )

    url = data["url"]

    await query.answer(f"{quality}p selected")
    await query.message.edit_text(f"⏳ Downloading in {quality}p...")

    filepath = None
    folder = os.path.join(DOWNLOAD_DIR, token)

    try:
        loop = asyncio.get_running_loop()
        filepath, title, ffmpeg_ok = await loop.run_in_executor(
            None,
            download_youtube_video,
            url,
            quality,
            token
        )

        if not filepath or not os.path.exists(filepath):
            return await query.message.edit_text("❌ Download failed. File nahi mili.")

        await query.message.edit_text("📤 Uploading to Telegram...")

        caption = (
            f"🎬 {title}\n"
            f"📺 Quality: {quality}p"
        )

        if not ffmpeg_ok and quality >= 720:
            caption += "\n\n⚠️ Server me ffmpeg nahi hai, 720p may not be perfect."

        try:
            await client.send_video(
                chat_id=query.message.chat.id,
                video=filepath,
                caption=caption,
                supports_streaming=True
            )
        except Exception:
            await client.send_document(
                chat_id=query.message.chat.id,
                document=filepath,
                caption=caption
            )

        await query.message.delete()

    except Exception as e:
        await query.message.edit_text(
            "❌ Download/upload error aaya.\n\n"
            f"Error:\n`{str(e)[:1000]}`"
        )

    finally:
        YT_CACHE.pop(token, None)

        if folder and os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception:
                pass


@Client.on_callback_query(filters.regex(r"^ytdl_cancel\|"))
async def yt_cancel_callback(client: Client, query: CallbackQuery):
    try:
        _, token = query.data.split("|")
    except Exception:
        return await query.answer("Invalid button.", show_alert=True)

    data = YT_CACHE.get(token)

    if data and query.from_user.id != data["user_id"]:
        return await query.answer(
            "Ye button tumhare liye nahi hai bro.",
            show_alert=True
        )

    YT_CACHE.pop(token, None)

    await query.answer("Cancelled")
    await query.message.edit_text("❌ Cancelled.")

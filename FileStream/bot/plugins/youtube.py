import os
import re
import time
import asyncio
import uuid
import shutil
from pathlib import Path

from pyrogram import Client, filters, StopPropagation
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

import yt_dlp


# ========== DEBUG COOKIES ON STARTUP ==========
print("=" * 60)
print("[COOKIES DEBUG] Starting check...")
print(f"[COOKIES DEBUG] Current directory: {os.getcwd()}")
print(f"[COOKIES DEBUG] Files with .txt or cookie:")
try:
    for f in os.listdir("."):
        if "cookie" in f.lower() or f.endswith(".txt"):
            size = os.path.getsize(f)
            print(f"[COOKIES DEBUG]   ✅ {f} ({size} bytes)")
except Exception as e:
    print(f"[COOKIES DEBUG]   Error listing: {e}")

# Check specific paths
paths_to_check = [
    "cookies.txt",
    "/app/cookies.txt",
    "./cookies.txt",
    "/cookies.txt",
]

for path in paths_to_check:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"[COOKIES DEBUG] ✅ FOUND: {path} ({size} bytes)")
        try:
            with open(path, "r") as f:
                first_line = f.readline().strip()
                print(f"[COOKIES DEBUG]    First line: {first_line[:80]}")
        except Exception as e:
            print(f"[COOKIES DEBUG]    Read error: {e}")
    else:
        print(f"[COOKIES DEBUG] ❌ NOT FOUND: {path}")

print("=" * 60)
# ========== END DEBUG ==========


DOWNLOAD_DIR = "downloads/youtube"
YT_CACHE = {}
CACHE_TIME = 1800

YOUTUBE_REGEX = re.compile(
    r"(https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)/[\w\-\?&=/.]+)",
    re.IGNORECASE
)


def cb_starts(prefix: str):
    return filters.create(
        lambda _, __, query: bool(query.data and query.data.startswith(prefix))
    )


def cleanup_cache():
    now = time.time()
    for token, data in list(YT_CACHE.items()):
        if now - data.get("time", now) > CACHE_TIME:
            YT_CACHE.pop(token, None)


def get_youtube_url(text: str):
    if not text:
        return None
    match = YOUTUBE_REGEX.search(text)
    return match.group(1) if match else None


def get_cookies_path():
    """Find cookies file - checks multiple paths"""
    
    # Check multiple possible locations
    possible_paths = [
        "cookies.txt",
        "/app/cookies.txt",
        "./cookies.txt",
        os.path.join(os.getcwd(), "cookies.txt"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 100:  # Valid cookies file should have content
                print(f"[YT] ✅ Cookies FOUND: {path} ({size} bytes)")
                return path
            else:
                print(f"[YT] ⚠️ Cookies too small: {path} ({size} bytes)")
    
    # Check env variable as fallback
    yt_env = os.getenv("YT_COOKIES")
    if yt_env:
        temp_path = "/tmp/yt_cookies.txt"
        try:
            with open(temp_path, "w") as f:
                f.write(yt_env)
            print(f"[YT] ✅ Cookies from ENV variable")
            return temp_path
        except Exception as e:
            print(f"[YT] ❌ ENV write error: {e}")
    
    print(f"[YT] ❌ NO COOKIES FOUND ANYWHERE")
    return None


def get_ydl_opts_base():
    """Base yt-dlp options"""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "restrictfilenames": True,
        "geo_bypass": True,
        "cachedir": False,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 5,
        "socket_timeout": 60,
        "nocheckcertificate": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "tv_embedded", "web"],
            }
        },
    }
    
    cookies_path = get_cookies_path()
    if cookies_path:
        opts["cookiefile"] = cookies_path
    
    return opts


def format_size(size_bytes):
    if not size_bytes:
        return "?"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def format_duration(seconds):
    if not seconds:
        return "Unknown"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ========== DEBUG COMMAND ==========
@Client.on_message(filters.command("cookiescheck"))
async def cookies_check_handler(client, message):
    """Debug: Check cookies status"""
    
    text = "🍪 **Cookies Debug**\n\n"
    text += f"📂 **CWD:** `{os.getcwd()}`\n\n"
    
    # Check paths
    text += "**📁 File Check:**\n"
    paths = [
        "cookies.txt",
        "/app/cookies.txt",
        "./cookies.txt",
    ]
    
    found = False
    for p in paths:
        if os.path.exists(p):
            size = os.path.getsize(p)
            text += f"✅ `{p}`\n   Size: `{size} bytes`\n"
            found = True
            try:
                with open(p, "r") as f:
                    first_line = f.readline().strip()
                    text += f"   Preview: `{first_line[:50]}...`\n"
            except:
                pass
        else:
            text += f"❌ `{p}`\n"
    
    text += "\n"
    
    # Check ENV
    yt_env = os.getenv("YT_COOKIES")
    if yt_env:
        text += f"✅ **ENV YT_COOKIES:** Set ({len(yt_env)} chars)\n"
    else:
        text += f"❌ **ENV YT_COOKIES:** Not set\n"
    
    text += "\n"
    
    # List cookie files
    text += "**🔍 Files in CWD:**\n"
    try:
        files = os.listdir(".")
        cookie_files = [f for f in files if "cookie" in f.lower()]
        txt_files = [f for f in files if f.endswith(".txt")]
        
        if cookie_files:
            for f in cookie_files:
                text += f"• `{f}`\n"
        else:
            text += f"No cookie files found\n"
        
        text += f"\n**📄 .txt files:**\n"
        if txt_files:
            for f in txt_files:
                text += f"• `{f}`\n"
        else:
            text += f"No .txt files\n"
    except Exception as e:
        text += f"Error: `{e}`\n"
    
    await message.reply_text(text)
# ========== END DEBUG ==========


async def get_video_info(url: str):
    opts = get_ydl_opts_base()
    opts["skip_download"] = True
    
    def _extract():
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, _extract)
    return info


def get_available_qualities(info):
    formats = info.get("formats", [])
    qualities = {}
    
    for f in formats:
        height = f.get("height")
        vcodec = f.get("vcodec", "none")
        
        if not height or vcodec == "none":
            continue
        if height < 144:
            continue
        
        if height <= 144:
            std = 144
        elif height <= 240:
            std = 240
        elif height <= 360:
            std = 360
        elif height <= 480:
            std = 480
        elif height <= 720:
            std = 720
        elif height <= 1080:
            std = 1080
        elif height <= 1440:
            std = 1440
        else:
            std = 2160
        
        if std not in qualities:
            qualities[std] = {
                "height": std,
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "ext": f.get("ext", "mp4"),
            }
        else:
            if f.get("filesize") and not qualities[std]["filesize"]:
                qualities[std]["filesize"] = f.get("filesize")
    
    return sorted(qualities.values(), key=lambda x: x["height"])


def build_quality_buttons(token: str, qualities: list):
    buttons = []
    target_qualities = [144, 240, 360, 480, 720, 1080, 1440, 2160]
    available = [q["height"] for q in qualities]
    row = []
    
    for quality in target_qualities:
        if quality in available:
            q_data = next(q for q in qualities if q["height"] == quality)
            if q_data["filesize"]:
                label = f"📥 {quality}p ({format_size(q_data['filesize'])})"
            else:
                label = f"📥 {quality}p"
            
            row.append(
                InlineKeyboardButton(
                    label,
                    callback_data=f"ytdl|{token}|{quality}"
                )
            )
            if len(row) == 2:
                buttons.append(row)
                row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(
            "🎵 MP3 Audio (192 kbps)",
            callback_data=f"ytmp3|{token}"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data=f"ytcancel|{token}"
        )
    ])
    
    return InlineKeyboardMarkup(buttons)


async def download_video(url: str, quality: int, token: str):
    folder = os.path.join(DOWNLOAD_DIR, token)
    Path(folder).mkdir(parents=True, exist_ok=True)
    
    opts = get_ydl_opts_base()
    opts.update({
        "format": (
            f"bestvideo[height<={quality}]+bestaudio/"
            f"best[height<={quality}]/"
            f"bestvideo+bestaudio/"
            f"best"
        ),
        "outtmpl": f"{folder}/%(title).60s.%(ext)s",
        "merge_output_format": "mp4",
        "no_check_formats": True,
    })
    
    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info
    
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, _download)
    
    for f in os.listdir(folder):
        if f.endswith(('.mp4', '.mkv', '.webm')):
            return os.path.join(folder, f), info
    
    return None, info


async def download_mp3(url: str, token: str):
    folder = os.path.join(DOWNLOAD_DIR, token)
    Path(folder).mkdir(parents=True, exist_ok=True)
    
    opts = get_ydl_opts_base()
    opts.update({
        "format": "bestaudio/best",
        "outtmpl": f"{folder}/%(title).60s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    })
    
    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info
    
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, _download)
    
    for f in os.listdir(folder):
        if f.endswith('.mp3'):
            return os.path.join(folder, f), info
    
    return None, info


def cleanup_download(token: str):
    folder = os.path.join(DOWNLOAD_DIR, token)
    if os.path.exists(folder):
        try:
            shutil.rmtree(folder)
        except Exception:
            pass


@Client.on_message(filters.command(["yt", "ytdl", "youtube"]))
async def yt_handler(client, message: Message):
    cleanup_cache()
    
    text = message.text or ""
    url = get_youtube_url(text)
    
    if not url and message.reply_to_message:
        reply_text = (message.reply_to_message.text or 
                     message.reply_to_message.caption or "")
        url = get_youtube_url(reply_text)
    
    if not url:
        return await message.reply_text(
            "❌ **YouTube link do**\n\n"
            "`/yt https://youtu.be/VIDEO_ID`"
        )
    
    msg = await message.reply_text("🔍 **Video info fetch...**")
    
    try:
        info = await get_video_info(url)
        
        title = info.get("title", "Unknown")
        uploader = info.get("uploader", "Unknown")
        duration = format_duration(info.get("duration"))
        view_count = info.get("view_count", 0)
        
        qualities = get_available_qualities(info)
        
        if not qualities:
            return await msg.edit_text("❌ **Koi quality nahi mili**")
        
        token = uuid.uuid4().hex[:10]
        YT_CACHE[token] = {
            "url": url,
            "title": title,
            "user_id": message.from_user.id if message.from_user else 0,
            "chat_id": message.chat.id,
            "reply_to": message.id,
            "time": time.time()
        }
        
        text = (
            f"🎬 **{title}**\n\n"
            f"👤 **Channel:** `{uploader}`\n"
            f"⏱ **Duration:** `{duration}`\n"
            f"👁 **Views:** `{view_count:,}`\n\n"
            f"📥 **Select quality:**"
        )
        
        await msg.edit_text(
            text,
            reply_markup=build_quality_buttons(token, qualities)
        )
        
    except Exception as e:
        error_msg = str(e)
        
        if "sign in" in error_msg.lower() or "not a bot" in error_msg.lower():
            await msg.edit_text(
                "❌ **Cookies Problem**\n\n"
                "Cookies load nahi ho rahi ya expire hai।\n\n"
                "Use `/cookiescheck` to debug\n\n"
                f"**Error:** `{error_msg[:200]}`"
            )
        else:
            await msg.edit_text(
                f"❌ **Error**\n\n`{error_msg[:400]}`"
            )


@Client.on_callback_query(cb_starts("ytdl|"), group=-999)
async def ytdl_callback(client, query: CallbackQuery):
    try:
        cleanup_cache()
        
        try:
            _, token, quality = query.data.split("|")
            quality = int(quality)
        except Exception:
            await query.answer("Invalid", show_alert=True)
            return
        
        data = YT_CACHE.get(token)
        if not data:
            await query.answer("Expired", show_alert=True)
            return
        
        if query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai", show_alert=True)
            return
        
        await query.answer(f"⬇️ {quality}p...")
        
        await query.message.edit_text(
            f"⬇️ **Downloading {quality}p...**\n\n"
            f"🎬 {data['title'][:60]}\n\n"
            f"⏳ Please wait..."
        )
        
        try:
            file_path, info = await download_video(data["url"], quality, token)
            
            if not file_path or not os.path.exists(file_path):
                await query.message.edit_text("❌ **Failed**")
                cleanup_download(token)
                return
            
            file_size = os.path.getsize(file_path)
            
            if file_size > 2000 * 1024 * 1024:
                await query.message.edit_text(
                    f"❌ **Too large** ({format_size(file_size)})"
                )
                cleanup_download(token)
                return
            
            await query.message.edit_text(
                f"📤 **Uploading...**\n\n"
                f"🎬 {data['title'][:60]}\n"
                f"📦 {format_size(file_size)}"
            )
            
            try:
                bot_info = await client.get_me()
                
                await client.send_video(
                    chat_id=data["chat_id"],
                    video=file_path,
                    caption=(
                        f"🎬 **{data['title']}**\n\n"
                        f"📺 `{quality}p`\n"
                        f"📦 `{format_size(file_size)}`\n\n"
                        f"⚡ @{bot_info.username}"
                    ),
                    reply_to_message_id=data["reply_to"],
                    supports_streaming=True
                )
                
                await query.message.delete()
                
            except Exception:
                await client.send_document(
                    chat_id=data["chat_id"],
                    document=file_path,
                    caption=f"🎬 **{data['title']}**",
                    reply_to_message_id=data["reply_to"]
                )
                await query.message.delete()
            
        except Exception as e:
            await query.message.edit_text(
                f"❌ **Error**\n\n`{str(e)[:400]}`"
            )
        
        finally:
            cleanup_download(token)
            YT_CACHE.pop(token, None)
    
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("ytmp3|"), group=-999)
async def ytmp3_callback(client, query: CallbackQuery):
    try:
        cleanup_cache()
        
        try:
            _, token = query.data.split("|")
        except Exception:
            await query.answer("Invalid", show_alert=True)
            return
        
        data = YT_CACHE.get(token)
        if not data:
            await query.answer("Expired", show_alert=True)
            return
        
        if query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai", show_alert=True)
            return
        
        await query.answer("🎵 MP3...")
        
        await query.message.edit_text(
            f"🎵 **Downloading MP3...**\n\n"
            f"🎬 {data['title'][:60]}"
        )
        
        try:
            file_path, info = await download_mp3(data["url"], token)
            
            if not file_path or not os.path.exists(file_path):
                await query.message.edit_text("❌ **MP3 failed**")
                cleanup_download(token)
                return
            
            file_size = os.path.getsize(file_path)
            
            await query.message.edit_text(
                f"📤 **Uploading MP3...**\n\n"
                f"🎵 {data['title'][:60]}\n"
                f"📦 {format_size(file_size)}"
            )
            
            bot_info = await client.get_me()
            
            await client.send_audio(
                chat_id=data["chat_id"],
                audio=file_path,
                caption=(
                    f"🎵 **{data['title']}**\n\n"
                    f"⚡ @{bot_info.username}"
                ),
                title=data['title'][:60],
                reply_to_message_id=data["reply_to"]
            )
            
            await query.message.delete()
            
        except Exception as e:
            await query.message.edit_text(
                f"❌ **MP3 error**\n\n`{str(e)[:400]}`"
            )
        
        finally:
            cleanup_download(token)
            YT_CACHE.pop(token, None)
    
    finally:
        raise StopPropagation


@Client.on_callback_query(cb_starts("ytcancel|"), group=-999)
async def ytcancel_callback(client, query: CallbackQuery):
    try:
        try:
            _, token = query.data.split("|")
        except Exception:
            await query.answer("Invalid", show_alert=True)
            return
        
        data = YT_CACHE.get(token)
        if data and query.from_user.id != data["user_id"]:
            await query.answer("Tumhare liye nahi hai", show_alert=True)
            return
        
        YT_CACHE.pop(token, None)
        cleanup_download(token)
        
        await query.answer("Cancelled")
        await query.message.edit_text("❌ **Cancelled**")
    
    finally:
        raise StopPropagation

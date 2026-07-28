"""
YouTube Downloader with Quality Buttons
Complete Working Solution
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import yt_dlp
import os
import asyncio

# Store video data temporarily
user_videos = {}

@Client.on_message(filters.command("yt") & filters.private)
async def youtube_download(client: Client, message: Message):
    """YouTube downloader with quality selection"""
    
    if len(message.command) < 2:
        return await message.reply_text(
            "**📥 YouTube Downloader**\n\n"
            "**Usage:** `/yt <YouTube URL>`\n\n"
            "**Example:**\n"
            "`/yt https://youtu.be/dQw4w9WgXcQ`\n\n"
            "**Features:**\n"
            "✅ Multiple quality options\n"
            "✅ Audio download\n"
            "✅ Direct links"
        )
    
    url = message.command[1]
    
    if not any(x in url for x in ['youtube.com', 'youtu.be']):
        return await message.reply_text("❌ Invalid YouTube URL!")
    
    status = await message.reply_text("⏳ **Fetching video info...**")
    
    try:
        # Get video info without downloading
        opts = {'quiet': True, 'no_warnings': True}
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: get_info(url, opts))
        
        if not info:
            return await status.edit_text("❌ **Failed to get video info!**")
        
        title = info.get('title', 'Video')[:60]
        duration = info.get('duration', 0)
        
        # Store data
        user_id = message.from_user.id
        user_videos[user_id] = {'url': url, 'title': title}
        
        # Quality buttons
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 1080p", callback_data=f"q:1080:{user_id}"),
                InlineKeyboardButton("📺 720p", callback_data=f"q:720:{user_id}")
            ],
            [
                InlineKeyboardButton("📱 480p", callback_data=f"q:480:{user_id}"),
                InlineKeyboardButton("📹 360p", callback_data=f"q:360:{user_id}")
            ],
            [
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"q:audio:{user_id}")
            ],
            [
                InlineKeyboardButton("🔗 Link Only", callback_data=f"q:link:{user_id}")
            ]
        ])
        
        await status.edit_text(
            f"**📹 {title}**\n\n"
            f"⏱️ Duration: {duration//60}:{duration%60:02d}\n\n"
            f"**Select Quality:**",
            reply_markup=buttons
        )
        
    except Exception as e:
        await status.edit_text(f"❌ Error: {str(e)[:100]}")


@Client.on_callback_query(filters.regex(r"^q:"))
async def handle_quality(client: Client, callback: CallbackQuery):
    """Handle quality button clicks"""
    
    data = callback.data.split(":")
    quality = data[1]
    user_id = int(data[2])
    
    if user_id not in user_videos:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    video_data = user_videos[user_id]
    url = video_data['url']
    title = video_data['title']
    
    await callback.answer(f"Processing {quality}...")
    
    msg = callback.message
    await msg.edit_text(f"📥 **Downloading {quality}...**")
    
    try:
        # Link only mode
        if quality == "link":
            link = await get_download_link(url)
            if link:
                await msg.edit_text(
                    f"**🔗 Direct Link**\n\n"
                    f"**Title:** {title}\n\n"
                    f"{link}\n\n"
                    f"⏱️ Valid for 6 hours\n"
                    f"Click to download 📱"
                )
            else:
                await msg.edit_text("❌ Failed to get link!")
            return
        
        # Download file
        if quality == "audio":
            file = await download_audio(url)
            file_type = "audio"
        else:
            file = await download_video(url, quality)
            file_type = "video"
        
        if not file or not os.path.exists(file):
            return await msg.edit_text("❌ Download failed!")
        
        # Size check
        size = os.path.getsize(file)
        if size > 2000000000:
            os.remove(file)
            return await msg.edit_text(
                f"❌ File too large: {size/1024/1024:.0f}MB\n"
                f"Use 'Link Only' option!"
            )
        
        # Upload
        await msg.edit_text("⏫ **Uploading...**")
        
        if file_type == "audio":
            await callback.message.reply_audio(
                audio=file,
                caption=f"🎵 {title}\n💾 {size/1024/1024:.1f}MB",
                title=title
            )
        else:
            await callback.message.reply_video(
                video=file,
                caption=f"📹 {title}\n🎬 {quality}\n💾 {size/1024/1024:.1f}MB",
                supports_streaming=True
            )
        
        os.remove(file)
        await msg.delete()
        
        # Cleanup
        if user_id in user_videos:
            del user_videos[user_id]
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:100]}")


def get_info(url, opts):
    """Get video info"""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except:
        return None


async def download_video(url, quality):
    """Download video with quality"""
    
    formats = {
        '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        '360': 'best[height<=360]'
    }
    
    opts = {
        'format': formats.get(quality, 'best'),
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: dl(url, opts))
    except:
        return None


async def download_audio(url):
    """Download audio only"""
    
    opts = {
        'format': 'bestaudio',
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        base = await loop.run_in_executor(None, lambda: dl(url, opts))
        if base:
            return base.rsplit('.', 1)[0] + '.mp3'
        return None
    except:
        return None


async def get_download_link(url):
    """Get direct link without downloading"""
    
    opts = {'format': 'best[height<=720]', 'quiet': True}
    
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: get_info(url, opts))
        if info:
            return info.get('url')
        return None
    except:
        return None


def dl(url, opts):
    """Download helper"""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        raise e

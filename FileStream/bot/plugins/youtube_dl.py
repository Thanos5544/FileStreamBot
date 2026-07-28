"""
YouTube Downloader Plugin - Production Ready
Features: Quality selection, Audio download, Direct links, Progress tracking
Author: @VisionnXBot
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import yt_dlp
import os
import asyncio
from datetime import datetime

# Store user video data temporarily
video_cache = {}

# Config
MAX_FILE_SIZE = 2000000000  # 2GB
DOWNLOAD_PATH = "/tmp"


# ==================== MAIN COMMAND ====================

@Client.on_message(filters.command("yt") & filters.private)
async def youtube_handler(client: Client, message: Message):
    """Main YouTube download command with quality selection"""
    
    # Check if URL provided
    if len(message.command) < 2:
        help_text = (
            "**📥 YouTube Downloader**\n\n"
            "**Usage:**\n"
            "`/yt <YouTube URL>`\n\n"
            "**Supported Platforms:**\n"
            "✅ YouTube\n"
            "✅ YouTube Shorts\n"
            "✅ YouTube Music\n\n"
            "**Features:**\n"
            "• Multiple quality options (360p-1080p)\n"
            "• Audio MP3 download\n"
            "• Direct download links\n"
            "• Fast & reliable\n\n"
            "**Example:**\n"
            "`/yt https://youtu.be/dQw4w9WgXcQ`"
        )
        return await message.reply_text(help_text)
    
    url = message.command[1]
    
    # Validate YouTube URL
    if not is_youtube_url(url):
        return await message.reply_text(
            "❌ **Invalid URL!**\n\n"
            "Please provide a valid YouTube link.\n\n"
            "**Supported formats:**\n"
            "• https://youtube.com/watch?v=xxxxx\n"
            "• https://youtu.be/xxxxx\n"
            "• https://youtube.com/shorts/xxxxx"
        )
    
    status_msg = await message.reply_text("⏳ **Fetching video info...**")
    
    try:
        # Get video information
        video_info = await fetch_video_info(url)
        
        if not video_info:
            return await status_msg.edit_text(
                "❌ **Failed to fetch video!**\n\n"
                "**Possible reasons:**\n"
                "• Invalid or private video\n"
                "• Age-restricted content\n"
                "• Deleted video\n"
                "• Region restricted\n\n"
                "Try another video or contact support."
            )
        
        # Extract video details
        title = video_info.get('title', 'Unknown')[:70]
        duration = video_info.get('duration', 0)
        views = video_info.get('view_count', 0)
        uploader = video_info.get('uploader', 'Unknown')
        thumbnail = video_info.get('thumbnail')
        
        # Format duration
        duration_str = format_duration(duration)
        views_str = format_views(views)
        
        # Store in cache
        user_id = message.from_user.id
        video_cache[user_id] = {
            'url': url,
            'title': title,
            'duration': duration,
            'thumbnail': thumbnail,
            'timestamp': datetime.now()
        }
        
        # Create quality buttons
        keyboard = create_quality_keyboard(user_id)
        
        # Send video info with quality options
        info_text = (
            f"**📹 {title}**\n\n"
            f"👤 **Uploader:** {uploader}\n"
            f"⏱️ **Duration:** {duration_str}\n"
            f"👁️ **Views:** {views_str}\n\n"
            f"**Select Quality:**"
        )
        
        await status_msg.edit_text(info_text, reply_markup=keyboard)
        
    except Exception as e:
        error_text = f"❌ **Error occurred:**\n`{str(e)[:150]}`"
        await status_msg.edit_text(error_text)


# ==================== CALLBACK HANDLER ====================

@Client.on_callback_query(filters.regex(r"^ytdl:"))
async def quality_callback_handler(client: Client, callback: CallbackQuery):
    """Handle quality button clicks"""
    
    # Parse callback data
    _, action, quality, user_id = callback.data.split(":")
    user_id = int(user_id)
    
    # Verify user
    if callback.from_user.id != user_id:
        return await callback.answer("❌ This is not for you!", show_alert=True)
    
    # Check if video data exists
    if user_id not in video_cache:
        return await callback.answer(
            "❌ Session expired! Send /yt again.",
            show_alert=True
        )
    
    video_data = video_cache[user_id]
    url = video_data['url']
    title = video_data['title']
    
    await callback.answer(f"⏬ Downloading {quality}...", show_alert=False)
    
    msg = callback.message
    await msg.edit_text(f"📥 **Downloading {quality}...**\n\nPlease wait...")
    
    try:
        # Handle different actions
        if action == "link":
            # Generate direct download link
            download_link = await generate_direct_link(url, quality)
            
            if download_link:
                link_text = (
                    f"**🔗 Direct Download Link**\n\n"
                    f"**Title:** {title}\n"
                    f"**Quality:** {quality}\n\n"
                    f"**Link:**\n`{download_link}`\n\n"
                    f"⏱️ **Valid for:** 6 hours\n"
                    f"📱 **Tip:** Click link to download in browser"
                )
                await msg.edit_text(link_text, disable_web_page_preview=True)
            else:
                await msg.edit_text("❌ Failed to generate link!")
            
            return
        
        # Download file
        if quality == "audio":
            file_path = await download_audio(url)
            media_type = "audio"
        else:
            file_path = await download_video(url, quality)
            media_type = "video"
        
        if not file_path or not os.path.exists(file_path):
            return await msg.edit_text("❌ **Download failed!**\n\nTry again or use another quality.")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            return await msg.edit_text(
                f"❌ **File too large!**\n\n"
                f"**Size:** {format_size(file_size)}\n"
                f"**Limit:** 2GB (Telegram)\n\n"
                f"💡 **Tip:** Use 'Direct Link' option or lower quality."
            )
        
        # Upload to Telegram
        await msg.edit_text("⏫ **Uploading to Telegram...**")
        
        caption = f"**📹 {title}**\n🎬 **Quality:** {quality}\n💾 **Size:** {format_size(file_size)}"
        
        if media_type == "audio":
            await callback.message.reply_audio(
                audio=file_path,
                caption=caption,
                title=title,
                duration=video_data.get('duration', 0),
                thumb=video_data.get('thumbnail')
            )
        else:
            await callback.message.reply_video(
                video=file_path,
                caption=caption,
                duration=video_data.get('duration', 0),
                supports_streaming=True,
                thumb=video_data.get('thumbnail')
            )
        
        # Cleanup
        os.remove(file_path)
        await msg.delete()
        
        # Remove from cache
        if user_id in video_cache:
            del video_cache[user_id]
        
    except Exception as e:
        error_msg = f"❌ **Error:**\n`{str(e)[:150]}`"
        await msg.edit_text(error_msg)
        
        # Cleanup on error
        if 'file_path' in locals() and file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


# ==================== HELPER FUNCTIONS ====================

def is_youtube_url(url: str) -> bool:
    """Check if URL is a valid YouTube link"""
    return any(domain in url for domain in ['youtube.com', 'youtu.be', 'youtube-nocookie.com'])


async def fetch_video_info(url: str) -> dict:
    """Fetch video information without downloading"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }
    
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: extract_info(url, opts)
        )
        return info
    except:
        return None


def extract_info(url: str, opts: dict) -> dict:
    """Extract video info using yt-dlp"""
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


async def download_video(url: str, quality: str) -> str:
    """Download video with specified quality"""
    
    quality_map = {
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        '360p': 'best[height<=360]'
    }
    
    opts = {
        'format': quality_map.get(quality, 'best'),
        'outtmpl': f'{DOWNLOAD_PATH}/%(id)s.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: download_file(url, opts))
    except:
        return None


async def download_audio(url: str) -> str:
    """Download audio only in MP3 format"""
    
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_PATH}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        base_path = await loop.run_in_executor(None, lambda: download_file(url, opts))
        if base_path:
            # Return MP3 path
            return os.path.splitext(base_path)[0] + '.mp3'
        return None
    except:
        return None


def download_file(url: str, opts: dict) -> str:
    """Download file using yt-dlp"""
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


async def generate_direct_link(url: str, quality: str) -> str:
    """Generate direct download link without downloading"""
    
    quality_map = {
        '1080p': 'best[height<=1080]',
        '720p': 'best[height<=720]',
        '480p': 'best[height<=480]',
        '360p': 'best[height<=360]'
    }
    
    opts = {
        'format': quality_map.get(quality, 'best'),
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: extract_info(url, opts))
        if info:
            return info.get('url', None)
        return None
    except:
        return None


def create_quality_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard with quality options"""
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 1080p", callback_data=f"ytdl:dl:1080p:{user_id}"),
            InlineKeyboardButton("📺 720p", callback_data=f"ytdl:dl:720p:{user_id}")
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data=f"ytdl:dl:480p:{user_id}"),
            InlineKeyboardButton("📹 360p", callback_data=f"ytdl:dl:360p:{user_id}")
        ],
        [
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"ytdl:dl:audio:{user_id}")
        ],
        [
            InlineKeyboardButton("🔗 Direct Link (720p)", callback_data=f"ytdl:link:720p:{user_id}")
        ]
    ])


def format_duration(seconds: int) -> str:
    """Format duration in HH:MM:SS"""
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_views(views: int) -> str:
    """Format view count"""
    if not views:
        return "Unknown"
    
    if views >= 1000000:
        return f"{views/1000000:.1f}M"
    elif views >= 1000:
        return f"{views/1000:.1f}K"
    else:
        return str(views)


def format_size(size: int) -> str:
    """Format file size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


# ==================== INFO COMMAND ====================

@Client.on_message(filters.command("ythelp") & filters.private)
async def youtube_help(client: Client, message: Message):
    """YouTube downloader help and information"""
    
    help_text = (
        "**📚 YouTube Downloader - Help**\n\n"
        "**Commands:**\n"
        "`/yt <URL>` - Download YouTube video\n"
        "`/ythelp` - Show this help message\n\n"
        "**Quality Options:**\n"
        "• **1080p** - Full HD (large file)\n"
        "• **720p** - HD (recommended)\n"
        "• **480p** - Standard (medium file)\n"
        "• **360p** - Low (small file)\n"
        "• **Audio** - MP3 format (192kbps)\n"
        "• **Direct Link** - No upload, browser download\n\n"
        "**Limits:**\n"
        "• Max file size: 2GB\n"
        "• Supported: YouTube only\n\n"
        "**Tips:**\n"
        "💡 Use 720p for best balance\n"
        "💡 Use Direct Link for large files\n"
        "💡 Audio mode saves data\n\n"
        "**Powered by:** @VisionnXBot 🔥"
    )
    
    await message.reply_text(help_text)

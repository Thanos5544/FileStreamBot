"""
YouTube Link Generator Plugin
No download, no data usage - just generates direct links!
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import asyncio

@Client.on_message(filters.command("ytlink") & filters.private)
async def youtube_link_generator(client: Client, message: Message):
    """Generate YouTube direct download links"""
    
    if len(message.command) < 2:
        help_text = (
            "**🔗 YouTube Link Generator**\n\n"
            "**Usage:**\n"
            "`/ytlink <YouTube URL>`\n\n"
            "**Features:**\n"
            "✅ No bot data usage\n"
            "✅ Direct download links\n"
            "✅ Multiple quality options\n"
            "✅ Fast & reliable\n\n"
            "**Example:**\n"
            "`/ytlink https://youtu.be/dQw4w9WgXcQ`\n\n"
            "💡 **You download directly - bot saves data!**"
        )
        return await message.reply_text(help_text)
    
    url = message.command[1]
    
    # Validate URL
    if not any(x in url for x in ['youtube.com', 'youtu.be']):
        return await message.reply_text("❌ Invalid YouTube URL!\n\nSupported: youtube.com, youtu.be")
    
    status = await message.reply_text("⏳ **Generating links...**")
    
    try:
        # Get video info and formats
        info = await get_video_info(url)
        
        if not info:
            return await status.edit_text(
                "❌ **Failed to fetch video!**\n\n"
                "Possible reasons:\n"
                "• Private or deleted video\n"
                "• Invalid URL\n"
                "• Try another video"
            )
        
        # Extract info
        title = info.get('title', 'Video')[:80]
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Unknown')
        thumbnail = info.get('thumbnail', '')
        
        # Format duration
        mins = duration // 60
        secs = duration % 60
        dur_str = f"{mins}:{secs:02d}"
        
        # Get quality options
        formats = info.get('formats', [])
        
        # Extract best links for each quality
        links = extract_quality_links(formats, info)
        
        # Create message
        link_text = (
            f"**📹 {title}**\n\n"
            f"👤 **Uploader:** {uploader}\n"
            f"⏱️ **Duration:** {dur_str}\n\n"
        )
        
        if links:
            link_text += "**🔗 Download Links:**\n\n"
            
            for quality, link in links.items():
                if link:
                    link_text += f"**{quality}:**\n`{link}`\n\n"
            
            link_text += (
                "⏱️ **Valid for:** 6 hours\n"
                "📱 **Tip:** Click link to download in browser\n\n"
                "💡 **No bot data used!** ✅"
            )
        else:
            link_text += "❌ No download links available!"
        
        # Create buttons
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 Audio Link", callback_data=f"audio_link:{url}")]
        ])
        
        await status.edit_text(link_text, reply_markup=buttons, disable_web_page_preview=True)
        
    except Exception as e:
        error_text = f"❌ **Error:**\n`{str(e)[:150]}`"
        await status.edit_text(error_text)


@Client.on_callback_query(filters.regex(r"^audio_link:"))
async def audio_link_handler(client: Client, callback):
    """Generate audio-only link"""
    
    url = callback.data.split(":", 1)[1]
    
    await callback.answer("Generating audio link...", show_alert=False)
    
    msg = callback.message
    await msg.edit_text("⏳ **Generating audio link...**")
    
    try:
        # Get audio link
        audio_link = await get_audio_link(url)
        
        if audio_link:
            audio_text = (
                "**🎵 Audio Download Link**\n\n"
                f"**Link:**\n`{audio_link}`\n\n"
                "⏱️ Valid for 6 hours\n"
                "📱 Click to download MP3\n\n"
                "💡 No bot data used! ✅"
            )
            await msg.edit_text(audio_text, disable_web_page_preview=True)
        else:
            await msg.edit_text("❌ Failed to generate audio link!")
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:100]}")


async def get_video_info(url: str):
    """Get video information without downloading"""
    
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'best'
    }
    
    try:
        loop = asyncio.get_event_loop()
        
        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        info = await loop.run_in_executor(None, extract)
        return info
    except:
        return None


def extract_quality_links(formats: list, info: dict) -> dict:
    """Extract best download links for each quality"""
    
    links = {}
    
    # Try to get direct video URL
    try:
        # Get best overall link (usually 720p or best available)
        best_url = info.get('url')
        if best_url:
            links['Best Quality'] = best_url
    except:
        pass
    
    # Try to extract specific qualities
    quality_map = {
        '1080p': 1080,
        '720p': 720,
        '480p': 480,
        '360p': 360
    }
    
    for quality_name, height in quality_map.items():
        for fmt in formats:
            if fmt.get('height') == height and fmt.get('url'):
                links[quality_name] = fmt['url']
                break
    
    return links


async def get_audio_link(url: str):
    """Get audio-only download link"""
    
    opts = {
        'format': 'bestaudio',
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        
        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('url')
        
        link = await loop.run_in_executor(None, extract)
        return link
    except:
        return None


@Client.on_message(filters.command("ythelp") & filters.private)
async def yt_help(client: Client, message: Message):
    """YouTube link generator help"""
    
    help_text = (
        "**📚 YouTube Link Generator - Help**\n\n"
        "**Command:**\n"
        "`/ytlink <YouTube URL>`\n\n"
        "**How it works:**\n"
        "1. Send YouTube link with /ytlink\n"
        "2. Bot generates direct download links\n"
        "3. Click link to download in browser\n"
        "4. No bot data used! ✅\n\n"
        "**Benefits:**\n"
        "✅ Zero bot data usage\n"
        "✅ Multiple quality options\n"
        "✅ Audio links available\n"
        "✅ Fast & reliable\n\n"
        "**Limitations:**\n"
        "• Links expire after 6 hours\n"
        "• Download directly on your device\n\n"
        "**Example:**\n"
        "`/ytlink https://youtu.be/dQw4w9WgXcQ`"
    )
    
    await message.reply_text(help_text)


print("✅ YouTube Link Generator Plugin Loaded!")

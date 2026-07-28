"""
YouTube Link Generator Plugin
Direct clickable download buttons!
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import yt_dlp
import asyncio

# ========== MAIN COMMAND ==========

@Client.on_message(filters.command("ytlink") & filters.private)
async def youtube_link_generator(client: Client, message: Message):
    """Generate YouTube direct download link"""
    
    if len(message.command) < 2:
        help_text = (
            "**🔗 YouTube Link Generator**\n\n"
            "**Usage:** `/ytlink <YouTube URL>`\n\n"
            "**Example:**\n"
            "`/ytlink https://youtu.be/dQw4w9WgXcQ`"
        )
        return await message.reply_text(help_text)
    
    url = message.command[1]
    
    if not any(x in url for x in ['youtube.com', 'youtu.be']):
        return await message.reply_text("❌ Invalid YouTube URL!")
    
    status = await message.reply_text("⏳ **Generating link...**")
    
    try:
        # Get video info and link
        result = await get_video_link(url)
        
        if not result:
            return await status.edit_text("❌ **Failed to generate link!**\n\nTry another video.")
        
        title = result['title']
        duration = result['duration']
        link = result['link']
        
        # Format duration
        mins = duration // 60
        secs = duration % 60
        dur_str = f"{mins}:{secs:02d}"
        
        # Create message
        link_text = (
            f"**📹 {title}**\n\n"
            f"⏱️ **Duration:** {dur_str}\n\n"
            f"**Click button below to download:**\n\n"
            f"⏱️ Valid for 6 hours\n"
            f"✅ No bot data used!"
        )
        
        # Create CLICKABLE buttons
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download Video", url=link)],
            [InlineKeyboardButton("🎵 Get Audio Link", callback_data=f"aud:{message.id}")]
        ])
        
        # Store URL for audio callback
        client.yt_cache = getattr(client, 'yt_cache', {})
        client.yt_cache[message.id] = url
        
        await status.edit_text(link_text, reply_markup=buttons)
        
    except Exception as e:
        await status.edit_text(f"❌ Error: {str(e)[:100]}")


# ========== AUDIO CALLBACK ==========

@Client.on_callback_query(filters.regex(r"^aud:"))
async def audio_callback(client: Client, callback: CallbackQuery):
    """Handle audio link request"""
    
    msg_id = int(callback.data.split(":")[1])
    
    # Get URL from cache
    cache = getattr(client, 'yt_cache', {})
    url = cache.get(msg_id)
    
    if not url:
        return await callback.answer("❌ Expired! Send /ytlink again.", show_alert=True)
    
    await callback.answer("⏬ Generating audio link...", show_alert=False)
    
    msg = callback.message
    await msg.edit_text("⏳ **Generating audio link...**")
    
    try:
        # Get audio link
        result = await get_audio_link(url)
        
        if not result:
            return await msg.edit_text("❌ Failed to generate audio link!")
        
        title = result['title']
        link = result['link']
        
        # Create audio message with button
        audio_text = (
            f"**🎵 {title}**\n\n"
            f"**Click button below to download MP3:**\n\n"
            f"⏱️ Valid for 6 hours\n"
            f"✅ No bot data used!"
        )
        
        # Audio download button
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download Audio (MP3)", url=link)]
        ])
        
        await msg.edit_text(audio_text, reply_markup=buttons)
        
        # Remove from cache
        if msg_id in cache:
            del cache[msg_id]
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:100]}")


# ========== HELPER FUNCTIONS ==========

async def get_video_link(url: str) -> dict:
    """Get video download link"""
    
    opts = {
        'format': 'best[height<=720]',
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        
        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Video')[:60],
                    'duration': info.get('duration', 0),
                    'link': info.get('url', '')
                }
        
        result = await loop.run_in_executor(None, extract)
        return result if result and result['link'] else None
            
    except:
        return None


async def get_audio_link(url: str) -> dict:
    """Get audio download link"""
    
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        
        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Audio')[:60],
                    'link': info.get('url', '')
                }
        
        result = await loop.run_in_executor(None, extract)
        return result if result and result['link'] else None
            
    except:
        return None


# ========== HELP ==========

@Client.on_message(filters.command("ythelp") & filters.private)
async def yt_help(client: Client, message: Message):
    help_text = (
        "**📚 YouTube Link Generator**\n\n"
        "`/ytlink <URL>` - Generate download links\n\n"
        "**How to use:**\n"
        "1. Send YouTube link\n"
        "2. Click download button\n"
        "3. Browser opens → Download starts\n\n"
        "✅ No bot data used!"
    )
    await message.reply_text(help_text)


print("✅ YouTube Link Generator (Button Version) Loaded!")

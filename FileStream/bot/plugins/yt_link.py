"""
YouTube Link Generator Plugin
Generates direct download links - No data usage!
Simple & Clean
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
            "**Usage:**\n"
            "`/ytlink <YouTube URL>`\n\n"
            "**Features:**\n"
            "✅ Direct download links\n"
            "✅ No bot data usage\n"
            "✅ Audio option available\n\n"
            "**Example:**\n"
            "`/ytlink https://youtu.be/dQw4w9WgXcQ`"
        )
        return await message.reply_text(help_text)
    
    url = message.command[1]
    
    # Validate URL
    if not any(x in url for x in ['youtube.com', 'youtu.be']):
        return await message.reply_text("❌ Invalid YouTube URL!\n\nSupported: youtube.com, youtu.be")
    
    status = await message.reply_text("⏳ **Generating link...**")
    
    try:
        # Get video info and link
        result = await get_video_link(url)
        
        if not result:
            return await status.edit_text(
                "❌ **Failed to generate link!**\n\n"
                "Possible reasons:\n"
                "• Invalid or private video\n"
                "• Deleted video\n"
                "• Try another link"
            )
        
        title = result['title']
        duration = result['duration']
        link = result['link']
        
        # Format duration
        mins = duration // 60
        secs = duration % 60
        dur_str = f"{mins}:{secs:02d}"
        
        # Create message with clickable link
        link_text = (
            f"**📹 {title}**\n\n"
            f"⏱️ **Duration:** {dur_str}\n\n"
            f"**🔗 Download Link:**\n"
            f"[Click Here to Download]({link})\n\n"
            f"⏱️ Valid for 6 hours\n"
            f"💡 Click → Browser → Download\n\n"
            f"✅ No bot data used!"
        )
        
        # Add audio button
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 Get Audio Link", callback_data=f"aud:{message.id}")]
        ])
        
        # Store URL for audio callback
        client.yt_cache = getattr(client, 'yt_cache', {})
        client.yt_cache[message.id] = url
        
        await status.edit_text(link_text, reply_markup=buttons, disable_web_page_preview=True)
        
    except Exception as e:
        error_msg = str(e)[:150]
        await status.edit_text(f"❌ **Error:**\n`{error_msg}`")


# ========== AUDIO CALLBACK ==========

@Client.on_callback_query(filters.regex(r"^aud:"))
async def audio_callback(client: Client, callback: CallbackQuery):
    """Handle audio link request"""
    
    msg_id = int(callback.data.split(":")[1])
    
    # Get URL from cache
    cache = getattr(client, 'yt_cache', {})
    url = cache.get(msg_id)
    
    if not url:
        return await callback.answer("❌ Session expired! Send /ytlink again.", show_alert=True)
    
    await callback.answer("⏬ Generating audio link...", show_alert=False)
    
    msg = callback.message
    await msg.edit_text("⏳ **Generating audio link...**")
    
    try:
        # Get audio link
        result = await get_audio_link(url)
        
        if not result:
            return await msg.edit_text("❌ **Failed to generate audio link!**")
        
        title = result['title']
        link = result['link']
        
        # Create audio message
        audio_text = (
            f"**🎵 {title}**\n\n"
            f"**🔗 Audio Link (MP3):**\n"
            f"[Click Here to Download]({link})\n\n"
            f"⏱️ Valid for 6 hours\n"
            f"💡 Click → Browser → Download\n\n"
            f"✅ No bot data used!"
        )
        
        await msg.edit_text(audio_text, disable_web_page_preview=True)
        
        # Remove from cache
        if msg_id in cache:
            del cache[msg_id]
        
    except Exception as e:
        await msg.edit_text(f"❌ **Error:**\n`{str(e)[:100]}`")


# ========== HELPER FUNCTIONS ==========

async def get_video_link(url: str) -> dict:
    """Get video download link"""
    
    opts = {
        'format': 'best[height<=720]',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
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
        
        if result and result['link']:
            return result
        else:
            return None
            
    except Exception as e:
        print(f"Video link error: {e}")
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
        
        if result and result['link']:
            return result
        else:
            return None
            
    except Exception as e:
        print(f"Audio link error: {e}")
        return None


# ========== HELP COMMAND ==========

@Client.on_message(filters.command("ythelp") & filters.private)
async def yt_help_command(client: Client, message: Message):
    """YouTube link generator help"""
    
    help_text = (
        "**📚 YouTube Link Generator**\n\n"
        "**Command:**\n"
        "`/ytlink <YouTube URL>`\n\n"
        "**How it works:**\n"
        "1. Send YouTube link\n"
        "2. Get direct download link\n"
        "3. Click to download in browser\n"
        "4. No bot data used! ✅\n\n"
        "**Features:**\n"
        "✅ Best quality (up to 720p)\n"
        "✅ Audio MP3 option\n"
        "✅ Fast & reliable\n"
        "✅ Zero bot data usage\n\n"
        "**Example:**\n"
        "`/ytlink https://youtu.be/dQw4w9WgXcQ`\n\n"
        "💡 **Tip:** Links expire after 6 hours"
    )
    
    await message.reply_text(help_text)


# ========== PLUGIN LOADED ==========

print("✅ YouTube Link Generator Plugin Loaded!")

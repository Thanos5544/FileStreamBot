"""
YouTube Link Generator - Complete with Quality Selection
Using Cobalt API for maximum success rate
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import aiohttp

COBALT_API = "https://api.cobalt.tools/api/json"

# Store user video data
video_cache = {}

# ==================== MAIN COMMAND ====================

@Client.on_message(filters.command("ytlink") & filters.private)
async def youtube_link_generator(client: Client, message: Message):
    """YouTube link generator with quality selection"""
    
    if len(message.command) < 2:
        help_text = (
            "**🔗 YouTube Link Generator**\n\n"
            "**Usage:**\n"
            "`/ytlink <YouTube URL>`\n\n"
            "**Features:**\n"
            "✅ Quality selection (360p - Max)\n"
            "✅ Audio MP3 download\n"
            "✅ No bot data usage\n\n"
            "**Example:**\n"
            "`/ytlink https://youtu.be/dQw4w9WgXcQ`"
        )
        return await message.reply_text(help_text)
    
    url = message.command[1]
    
    # Validate URL
    if not any(x in url for x in ['youtube.com', 'youtu.be']):
        return await message.reply_text("❌ Invalid YouTube URL!\n\nSupported: youtube.com, youtu.be")
    
    status = await message.reply_text("⏳ **Processing...**")
    
    try:
        # Store URL
        user_id = message.from_user.id
        video_cache[user_id] = {'url': url}
        
        # Show quality selection buttons
        await show_quality_options(status, user_id)
        
    except Exception as e:
        await status.edit_text(f"❌ Error: {str(e)[:100]}")


def show_quality_options(message, user_id: int):
    """Show quality selection buttons"""
    
    text = (
        "**📹 YouTube Video**\n\n"
        "**Select Quality:**\n\n"
        "💡 Higher quality = larger file size\n"
        "✅ No bot data used!"
    )
    
    # Quality buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Max Quality", callback_data=f"ytq:max:{user_id}"),
            InlineKeyboardButton("📺 720p HD", callback_data=f"ytq:720:{user_id}")
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data=f"ytq:480:{user_id}"),
            InlineKeyboardButton("📹 360p", callback_data=f"ytq:360:{user_id}")
        ],
        [
            InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data=f"ytq:audio:{user_id}")
        ]
    ])
    
    return message.edit_text(text, reply_markup=buttons)


# ==================== QUALITY CALLBACK ====================

@Client.on_callback_query(filters.regex(r"^ytq:"))
async def quality_callback_handler(client: Client, callback: CallbackQuery):
    """Handle quality selection"""
    
    data = callback.data.split(":")
    quality = data[1]
    user_id = int(data[2])
    
    # Verify user
    if callback.from_user.id != user_id:
        return await callback.answer("❌ Not for you!", show_alert=True)
    
    # Check cache
    if user_id not in video_cache:
        return await callback.answer("❌ Expired! Send /ytlink again.", show_alert=True)
    
    url = video_cache[user_id]['url']
    
    await callback.answer(f"⏬ Generating {quality} link...", show_alert=False)
    
    msg = callback.message
    await msg.edit_text(f"⏳ **Generating {quality} link...**")
    
    try:
        # Generate link based on quality
        if quality == "audio":
            download_url = await get_audio_link(url)
            quality_text = "Audio (MP3)"
        else:
            download_url = await get_video_link(url, quality)
            quality_text = quality.upper()
        
        if not download_url:
            # Failed - show retry options
            error_text = (
                f"❌ **Failed to generate {quality_text} link!**\n\n"
                "**Try:**\n"
                "• Different quality (button below)\n"
                "• Another video\n\n"
                "⚠️ Some videos are restricted"
            )
            
            # Retry button
            retry_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Other Quality", callback_data=f"retry:{user_id}")]
            ])
            
            return await msg.edit_text(error_text, reply_markup=retry_btn)
        
        # Success - show download button
        success_text = (
            f"**✅ Link Generated!**\n\n"
            f"📹 **Quality:** {quality_text}\n\n"
            f"**Click button to download:**\n\n"
            f"⏱️ Valid for 6 hours\n"
            f"💡 Opens in browser\n"
            f"✅ No bot data used!"
        )
        
        # Download button
        download_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download Now", url=download_url)],
            [InlineKeyboardButton("🔄 Change Quality", callback_data=f"retry:{user_id}")]
        ])
        
        await msg.edit_text(success_text, reply_markup=download_btn)
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:100]}")


# ==================== RETRY CALLBACK ====================

@Client.on_callback_query(filters.regex(r"^retry:"))
async def retry_callback(client: Client, callback: CallbackQuery):
    """Show quality options again"""
    
    user_id = int(callback.data.split(":")[1])
    
    if callback.from_user.id != user_id:
        return await callback.answer("❌ Not for you!", show_alert=True)
    
    if user_id not in video_cache:
        return await callback.answer("❌ Expired!", show_alert=True)
    
    await callback.answer("Select quality again", show_alert=False)
    await show_quality_options(callback.message, user_id)


# ==================== API FUNCTIONS ====================

async def get_video_link(url: str, quality: str) -> str:
    """Get video download link from Cobalt API"""
    
    # Quality mapping
    quality_map = {
        "max": "max",
        "720": "720",
        "480": "480",
        "360": "360"
    }
    
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": quality_map.get(quality, "720"),
        "aFormat": "mp3",
        "isAudioOnly": False,
        "filenamePattern": "basic"
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                COBALT_API,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                status = data.get('status')
                
                # Success cases
                if status == 'redirect' or status == 'stream':
                    return data.get('url')
                
                elif status == 'picker':
                    # Multiple videos (carousel)
                    picker = data.get('picker', [])
                    if picker:
                        return picker[0].get('url')
                
                return None
                
    except Exception as e:
        print(f"Cobalt video error: {e}")
        return None


async def get_audio_link(url: str) -> str:
    """Get audio download link from Cobalt API"""
    
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "720",
        "aFormat": "mp3",
        "isAudioOnly": True,
        "filenamePattern": "basic"
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                COBALT_API,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                status = data.get('status')
                
                if status == 'redirect' or status == 'stream':
                    return data.get('url')
                
                return None
                
    except Exception as e:
        print(f"Cobalt audio error: {e}")
        return None


# ==================== HELP COMMAND ====================

@Client.on_message(filters.command("ythelp") & filters.private)
async def yt_help_command(client: Client, message: Message):
    """Help command"""
    
    help_text = (
        "**📚 YouTube Link Generator - Help**\n\n"
        "**Command:**\n"
        "`/ytlink <YouTube URL>`\n\n"
        "**How to use:**\n"
        "1. Send YouTube link with /ytlink\n"
        "2. Select quality from buttons\n"
        "3. Click download button\n"
        "4. Browser opens → Download starts\n\n"
        "**Quality Options:**\n"
        "• **Max Quality** - Best available\n"
        "• **720p HD** - High quality\n"
        "• **480p** - Medium quality\n"
        "• **360p** - Low quality (small file)\n"
        "• **Audio MP3** - Audio only\n\n"
        "**Features:**\n"
        "✅ No bot data usage\n"
        "✅ Direct browser download\n"
        "✅ Multiple quality options\n"
        "✅ Retry if failed\n\n"
        "**Note:**\n"
        "⚠️ Some videos may not work due to:\n"
        "• Age restrictions\n"
        "• Region blocks\n"
        "• Copyright protection\n\n"
        "💡 Try different quality if one fails!"
    )
    
    await message.reply_text(help_text)


# ==================== STATS ====================

@Client.on_message(filters.command("ytstats") & filters.private)
async def yt_stats(client: Client, message: Message):
    """Show stats"""
    
    cache_size = len(video_cache)
    
    stats_text = (
        "**📊 YouTube Link Generator Stats**\n\n"
        f"🔢 Active sessions: {cache_size}\n"
        f"🌐 API: Cobalt.tools\n"
        f"✅ Status: Online\n\n"
        f"**Powered by Cobalt API** 🔥"
    )
    
    await message.reply_text(stats_text)


print("✅ YouTube Link Generator (Quality Buttons) Loaded!")

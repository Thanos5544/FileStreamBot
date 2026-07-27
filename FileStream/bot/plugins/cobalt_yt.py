from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import os

# Cobalt API - FREE, NO TOKEN NEEDED!
COBALT_API = "https://api.cobalt.tools/api/json"

@Client.on_message(filters.command("ytd") & filters.private)
async def cobalt_download(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**📥 Video Downloader**\n\n"
            "Usage: /ytd <URL>\n\n"
            "Supports: YouTube, Instagram, TikTok, Twitter, Reddit\n\n"
            "Example: /ytd https://youtu.be/xxxxx"
        )
    
    url = message.command[1]
    status = await message.reply_text("⏳ Processing...")
    
    try:
        # Get download URL from Cobalt
        await status.edit_text("🔍 Fetching video...")
        
        video_url = await get_cobalt_url(url)
        
        if not video_url:
            return await status.edit_text(
                "❌ Failed to process!\n\n"
                "Possible reasons:\n"
                "• Invalid URL\n"
                "• Private/Deleted video\n"
                "• Unsupported platform"
            )
        
        # Download
        await status.edit_text("📥 Downloading...")
        filepath = await download_file(video_url)
        
        if not filepath:
            return await status.edit_text("❌ Download failed!")
        
        # Check size
        size = os.path.getsize(filepath)
        if size > 2097152000:  # 2GB
            os.remove(filepath)
            return await status.edit_text(f"❌ File too large: {size/1024/1024:.0f}MB")
        
        # Upload
        await status.edit_text("⏫ Uploading...")
        
        await message.reply_video(
            video=filepath,
            caption=f"📹 Downloaded via Cobalt\n💾 Size: {size/1024/1024:.1f}MB",
            supports_streaming=True
        )
        
        os.remove(filepath)
        await status.delete()
        
    except Exception as e:
        await status.edit_text(f"❌ Error: {str(e)[:100]}")
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)


async def get_cobalt_url(url):
    """Get download URL from Cobalt API"""
    
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "720",
        "aFormat": "mp3",
        "isAudioOnly": False,
        "isTTFullAudio": False
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(COBALT_API, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Check response status
                    status = data.get('status')
                    
                    if status == 'redirect' or status == 'stream':
                        return data.get('url')
                    elif status == 'picker':
                        # Multiple files (e.g., Instagram carousel)
                        picker = data.get('picker', [])
                        if picker and len(picker) > 0:
                            return picker[0].get('url')
                
                return None
                
    except Exception as e:
        print(f"Cobalt error: {e}")
        return None


async def download_file(url):
    """Download video from URL"""
    
    filepath = f"/tmp/video_{os.urandom(4).hex()}.mp4"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status == 200:
                    with open(filepath, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                    
                    return filepath
    except Exception as e:
        print(f"Download error: {e}")
    
    return None

from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import asyncio
import os

# APIFY CONFIG - APNA TOKEN YAHA DAAL
APIFY_TOKEN = "apify_api_z9BaFecKAbcMzrUCN6dFxr96ex4moo3YKcbq"  # ← YAHA TOKEN PASTE KAR

@Client.on_message(filters.command("ytd") & filters.private)
async def apify_download(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/ytd <YouTube URL>`")
    
    url = message.command[1]
    status = await message.reply("⏳ Processing...")
    
    try:
        # Step 1: Apify se video info nikaal
        await status.edit("📡 Fetching from Apify...")
        video_data = await get_video_from_apify(url)
        
        if not video_data:
            return await status.edit("❌ Failed to get video!")
        
        download_url = video_data.get('url')
        title = video_data.get('title', 'Video')[:50]
        
        # Step 2: Download
        await status.edit("📥 Downloading...")
        file = await download_file(download_url, title)
        
        if not file:
            return await status.edit("❌ Download failed!")
        
        # Step 3: Upload
        await status.edit("⏫ Uploading...")
        await message.reply_video(
            video=file,
            caption=f"📹 **{title}**",
            supports_streaming=True
        )
        
        os.remove(file)
        await status.delete()
        
    except Exception as e:
        await status.edit(f"❌ Error: {str(e)[:100]}")


async def get_video_from_apify(url):
    """Apify se video data fetch karo"""
    
    # Apify Actor endpoint
    actor_url = f"https://api.apify.com/v2/acts/streamhunters~youtube-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    payload = {
        "startUrls": [url],
        "maxResults": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(actor_url, json=payload, timeout=120) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data and len(data) > 0:
                    return data[0]
    return None


async def download_file(url, title):
    """File download karo"""
    filepath = f"/tmp/{title}.mp4"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(filepath, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        f.write(chunk)
                return filepath
    return None

from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import asyncio
import os

# APIFY TOKEN YAHA DAAL
APIFY_TOKEN = "apify_api_z9BaFecKAbcMzrUCN6dFxr96ex4moo3YKcbq"

@Client.on_message(filters.command("ytd") & filters.private)
async def apify_download(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**📥 Apify YouTube Downloader**\n\n"
            "Usage: /ytd <YouTube URL>\n\n"
            "Example: /ytd https://youtu.be/xxxxx"
        )
    
    url = message.command[1]
    status = await message.reply_text("⏳ Processing...")
    
    try:
        # Apify API call
        await status.edit_text("📡 Connecting to Apify...")
        
        # Method: Direct yt-dlp with Apify proxy
        video_info = await fetch_from_apify(url)
        
        if not video_info:
            return await status.edit_text("❌ Failed to fetch video!\n\nTry another URL.")
        
        download_url = video_info.get('url')
        title = video_info.get('title', 'Video')[:50]
        
        if not download_url:
            return await status.edit_text("❌ No download URL found!")
        
        # Download
        await status.edit_text("📥 Downloading...")
        filepath = await download_video(download_url, title)
        
        if not filepath:
            return await status.edit_text("❌ Download failed!")
        
        # Check size
        size = os.path.getsize(filepath)
        if size > 2000000000:
            os.remove(filepath)
            return await status.edit_text(f"❌ File too large: {size/1024/1024:.1f}MB")
        
        # Upload
        await status.edit_text("⏫ Uploading...")
        await message.reply_video(
            video=filepath,
            caption=f"📹 {title}",
            supports_streaming=True
        )
        
        os.remove(filepath)
        await status.delete()
        
    except Exception as e:
        await status.edit_text(f"❌ Error:\n{str(e)[:150]}")


async def fetch_from_apify(url):
    """Apify se video data fetch"""
    
    # Apify YouTube Scraper Actor
    api_url = f"https://api.apify.com/v2/acts/streamhunters~youtube-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    payload = {
        "startUrls": [url],
        "maxResults": 1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0:
                        return {
                            'url': data[0].get('url') or data[0].get('videoUrl'),
                            'title': data[0].get('title')
                        }
    except:
        pass
    
    return None


async def download_video(url, title):
    """Download video file"""
    
    safe_title = "".join(c for c in title if c.isalnum() or c in ' -_')[:40]
    filepath = f"/tmp/{safe_title}.mp4"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(filepath, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                    return filepath
    except:
        pass
    
    return None

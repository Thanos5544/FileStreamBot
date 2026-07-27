from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import os

@Client.on_message(filters.command("yt") & filters.private)
async def yt_download(bot, message):
    if len(message.command) < 2:
        return await message.reply(
            "**📥 YouTube Downloader**\n\n"
            "**Usage:** `/yt <link>`\n"
            "**Example:** `/yt https://youtu.be/xxxxx`"
        )
    
    url = message.command[1]
    status = await message.reply("⏳ Downloading...")
    
    filename = None
    try:
        ydl_opts = {
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best',
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            info = ytdl.extract_info(url, download=True)
            filename = ytdl.prepare_filename(info)
            title = info.get('title', 'Video')
            duration = info.get('duration', 0)
        
        size = os.path.getsize(filename)
        if size > 2097152000:
            await status.edit("❌ File too large (>2GB)")
            os.remove(filename)
            return
        
        await status.edit("⏫ Uploading...")
        
        await message.reply_video(
            video=filename,
            caption=f"📹 **{title}**",
            duration=duration,
            supports_streaming=True
        )
        
        os.remove(filename)
        await status.delete()
        
    except Exception as e:
        await status.edit(f"❌ Error: `{str(e)}`")
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass


@Client.on_message(filters.command("ytaudio") & filters.private)
async def yt_audio(bot, message):
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/ytaudio <link>`")
    
    url = message.command[1]
    status = await message.reply("⏳ Downloading audio...")
    
    filename = None
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            info = ytdl.extract_info(url, download=True)
            base = ytdl.prepare_filename(info)
            filename = os.path.splitext(base)[0] + '.mp3'
            title = info.get('title', 'Audio')
        
        await status.edit("⏫ Uploading...")
        
        await message.reply_audio(
            audio=filename,
            caption=f"🎵 **{title}**",
            duration=info.get('duration', 0)
        )
        
        os.remove(filename)
        await status.delete()
        
    except Exception as e:
        await status.edit(f"❌ Error: `{str(e)}`")
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

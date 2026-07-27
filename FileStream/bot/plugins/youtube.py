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
            'format': '(bv*[height<=720]+ba/b[height<=720]/bv*+ba/b)',
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            info = ytdl.extract_info(url, download=True)
            filename = ytdl.prepare_filename(info)
            title = info.get('title', 'Video')
            duration = info.get('duration', 0)
        
        if not os.path.exists(filename):
            await status.edit("❌ Download failed!")
            return
            
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
        error_msg = str(e)
        if "Requested format is not available" in error_msg:
            await status.edit("❌ Video format not available. Try another video or contact admin.")
        else:
            await status.edit(f"❌ Error: `{error_msg[:200]}`")
        
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
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'restrictfilenames': True,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
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
        await status.edit(f"❌ Error: `{str(e)[:200]}`")
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass


@Client.on_message(filters.command("ytdl") & filters.private)
async def yt_simple(bot, message):
    """Backup command - downloads whatever format available"""
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/ytdl <link>`")
    
    url = message.command[1]
    status = await message.reply("⏳ Downloading (any format)...")
    
    filename = None
    try:
        ydl_opts = {
            'format': 'best',  # Simple - jo bhi best mile
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            info = ytdl.extract_info(url, download=True)
            filename = ytdl.prepare_filename(info)
            title = info.get('title', 'Video')
        
        await status.edit("⏫ Uploading...")
        
        # Check if video or audio
        ext = filename.split('.')[-1].lower()
        if ext in ['mp4', 'mkv', 'webm', 'avi']:
            await message.reply_video(video=filename, caption=f"📹 **{title}**")
        else:
            await message.reply_document(document=filename, caption=f"📄 **{title}**")
        
        os.remove(filename)
        await status.delete()
        
    except Exception as e:
        await status.edit(f"❌ Error: `{str(e)[:200]}`")
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

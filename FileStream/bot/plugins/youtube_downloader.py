"""
YouTube Downloader Plugin for FileStreamBot
Command: /yt <youtube_url>
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
import logging

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

DOWNLOAD_FOLDER = "downloads"
Path(DOWNLOAD_FOLDER).mkdir(exist_ok=True)

user_data = {}


class YTDownloader:
    @staticmethod
    def get_info(url):
        try:
            result = subprocess.run(
                ['yt-dlp', '--dump-json', '-f', 'best[ext=mp4]', url],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return None
            
            data = json.loads(result.stdout)
            
            formats = []
            for fmt in data.get('formats', [])[:15]:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    formats.append({
                        'id': fmt['format_id'],
                        'quality': f"{fmt.get('height', '?')}p",
                        'size': fmt.get('filesize', 0)
                    })
            
            seen = set()
            unique = []
            for fmt in sorted(formats, key=lambda x: x['size'], reverse=True):
                if fmt['quality'] not in seen:
                    seen.add(fmt['quality'])
                    unique.append(fmt)
            
            return {
                'title': data.get('title'),
                'duration': data.get('duration', 0),
                'uploader': data.get('uploader'),
                'formats': unique[:8],
                'direct': data.get('url')
            }
        except:
            return None
    
    @staticmethod
    def download(url, fmt_id):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"{DOWNLOAD_FOLDER}/video_{ts}.mp4"
            
            subprocess.run(
                ['yt-dlp', '-f', fmt_id, '-o', output, '--quiet', url],
                timeout=600, check=True
            )
            
            if os.path.exists(output):
                return output
            return None
        except:
            return None


@Client.on_message(filters.command("yt"))
async def yt_command(client, message):
    """
    /yt <youtube_url>
    """
    
    try:
        if len(message.command) < 2:
            await message.reply_text(
                "❌ **Usage:** `/yt <YouTube URL>`\n\n"
                "**Example:**\n"
                "`/yt https://youtu.be/dQw4w9WgXcQ`"
            )
            return
        
        url = message.command[1]
        
        if 'youtu' not in url:
            await message.reply_text("❌ YouTube link दो बhai!")
            return
        
        msg = await message.reply_text("⏳ Processing...")
        
        info = YTDownloader.get_info(url)
        
        if not info:
            await msg.edit_text("❌ Video नहीं मिला या link invalid है")
            return
        
        user_data[message.from_user.id] = {'url': url, 'info': info}
        
        # Buttons
        buttons = []
        for fmt in info['formats'][:8]:
            size = fmt['size'] / (1024*1024) if fmt['size'] else 0
            buttons.append([
                InlineKeyboardButton(
                    f"📥 {fmt['quality']} ({size:.0f}MB)",
                    callback_data=f"ytdl_{fmt['id']}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton("🔗 Direct Link", callback_data="ytdirect")
        ])
        
        text = f"""
🎬 **{info['title'][:60]}**

👤 {info['uploader'][:40]}
⏱️ {info['duration']//60} min

**Choose Quality:**
        """
        
        await msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


@Client.on_callback_query(filters.regex("^ytdl_|^ytdirect"))
async def yt_callback(client, query):
    uid = query.from_user.id
    
    if uid not in user_data:
        await query.answer("❌ Session expired!", show_alert=True)
        return
    
    url = user_data[uid]['url']
    info = user_data[uid]['info']
    
    if query.data == "ytdirect":
        await query.answer()
        await query.edit_message_text(
            f"🔗 **Direct Google Link:**\n\n`{info['direct'][:100]}...`",
            parse_mode='markdown'
        )
        return
    
    fmt_id = query.data.split('_')[1]
    
    await query.answer()
    await query.edit_message_text("⏳ Downloading...")
    
    try:
        file = YTDownloader.download(url, fmt_id)
        
        if not file:
            await query.edit_message_text("❌ Download failed")
            return
        
        await client.send_video(
            query.message.chat_id,
            file,
            caption=f"✅ {info['title'][:60]}"
        )
        
        await query.edit_message_text("✅ Done!")
        
        if os.path.exists(file):
            os.remove(file)
    
    except Exception as e:
        await query.edit_message_text(f"❌ {str(e)}")

import asyncio
import time
import aiohttp
from pyrogram import filters
from FileStream.bot import FileStream


@FileStream.on_message(filters.command("admtest"))
async def adm_test(_, m):
    """
    Test karta hai ki ADM/IDM use karne pe kitni speed milegi.
    Bot khud apne stream link se 16 parallel requests karta hai.
    Use: /admtest <stream_link>
    """
    
    if len(m.command) < 2:
        return await m.reply_text(
            "❌ **Usage:**\n\n"
            "`/admtest <stream_link>`\n\n"
            "**Steps:**\n"
            "1. Bot ko koi file bhejo\n"
            "2. Link generate hoga (stream link)\n"
            "3. Us link ko copy karke:\n"
            "`/admtest https://your-bot.koyeb.app/dl/xxxxx`\n\n"
            "Ye simulate karega ADM/IDM ki speed."
        )
    
    url = m.command[1]
    
    if not url.startswith("http"):
        return await m.reply_text("❌ **Invalid URL**\n\nStream link do (http... se start hona chahiye)")
    
    msg = await m.reply_text(
        f"⚡ **ADM/IDM Sɪᴍᴜʟᴀᴛᴏʀ**\n\n"
        f"🎯 Testing with **16 parallel connections**\n"
        f"⏳ Downloading 100 MB..."
    )
    
    # 16 parallel connections (jaise ADM karta hai)
    NUM_CONNECTIONS = 16
    TOTAL_SIZE = 100 * 1024 * 1024  # 100 MB test
    CHUNK_PER_CONNECTION = TOTAL_SIZE // NUM_CONNECTIONS
    
    async def download_chunk(session, start, end, connection_id):
        """Ek chunk download karta hai specific range se"""
        try:
            headers = {"Range": f"bytes={start}-{end}"}
            chunk_start = time.time()
            total_bytes = 0
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    total_bytes += len(chunk)
            
            chunk_time = time.time() - chunk_start
            chunk_speed = (total_bytes / 1024 / 1024) / chunk_time if chunk_time > 0 else 0
            
            return {
                "id": connection_id,
                "bytes": total_bytes,
                "time": chunk_time,
                "speed": chunk_speed,
                "success": True
            }
        except Exception as e:
            return {
                "id": connection_id,
                "success": False,
                "error": str(e)[:50]
            }
    
    try:
        # Start parallel downloads
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(NUM_CONNECTIONS):
                start = i * CHUNK_PER_CONNECTION
                end = start + CHUNK_PER_CONNECTION - 1
                if i == NUM_CONNECTIONS - 1:
                    end = TOTAL_SIZE - 1
                
                tasks.append(download_chunk(session, start, end, i + 1))
            
            results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Calculate stats
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        total_downloaded = sum(r["bytes"] for r in successful)
        total_mb = total_downloaded / 1024 / 1024
        combined_speed = total_mb / total_time
        
        avg_conn_speed = sum(r["speed"] for r in successful) / len(successful) if successful else 0
        max_conn_speed = max((r["speed"] for r in successful), default=0)
        
        # Format result
        text = f"🚀 **ADM/IDM Sɪᴍᴜʟᴀᴛᴏʀ Rᴇsᴜʟᴛs**\n\n"
        text += f"📊 **Connections:** `{NUM_CONNECTIONS}` (like ADM)\n"
        text += f"✅ **Successful:** `{len(successful)}/{NUM_CONNECTIONS}`\n"
        text += f"❌ **Failed:** `{len(failed)}`\n\n"
        text += f"📥 **Downloaded:** `{round(total_mb, 2)} MB`\n"
        text += f"⏱ **Total Time:** `{round(total_time, 2)} sec`\n\n"
        text += f"⚡ **Per Connection Avg:** `{round(avg_conn_speed, 2)} MB/s`\n"
        text += f"🏆 **Per Connection Max:** `{round(max_conn_speed, 2)} MB/s`\n\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"🚀 **COMBINED SPEED: `{round(combined_speed, 2)} MB/s`** ⚡\n\n"
        text += f"💡 _Yehi speed tumhe ADM/IDM se milegi_\n"
        text += f"🎯 _Server capacity aur bots ki real performance_"
        
        await msg.edit_text(text)
        
    except Exception as e:
        await msg.edit_text(f"❌ **Error:**\n`{str(e)[:300]}`")

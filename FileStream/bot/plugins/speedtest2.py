import asyncio
import time
import aiohttp
from pyrogram import filters
from FileStream.bot import FileStream


@FileStream.on_message(filters.command("admspeed"))
async def adm_speed(_, m):
    """Test parallel download speed automatically"""
    
    msg = await m.reply_text("⚡ Tᴇsᴛɪɴɢ ADM/IDM Sɪᴍᴜʟᴀᴛɪᴏɴ...\n\n16 parallel connections")
    
    # 100 MB test file from OVH
    url = "https://proof.ovh.net/files/100Mb.dat"
    NUM_CONNECTIONS = 16
    FILE_SIZE = 100 * 1024 * 1024
    CHUNK_SIZE = FILE_SIZE // NUM_CONNECTIONS
    
    async def download_range(session, start, end, cid):
        try:
            headers = {"Range": f"bytes={start}-{end}"}
            total = 0
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    total += len(chunk)
            
            return total
        except:
            return 0
    
    try:
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(NUM_CONNECTIONS):
                start = i * CHUNK_SIZE
                end = start + CHUNK_SIZE - 1
                tasks.append(download_range(session, start, end, i))
            
            results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        total_bytes = sum(results)
        total_mb = total_bytes / 1024 / 1024
        speed = total_mb / total_time
        
        await msg.edit_text(
            f"🚀 **ADM/IDM Sɪᴍᴜʟᴀᴛᴏʀ**\n\n"
            f"📊 Parallel Connections: `{NUM_CONNECTIONS}`\n"
            f"📥 Downloaded: `{round(total_mb, 2)} MB`\n"
            f"⏱ Time: `{round(total_time, 2)} sec`\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ **Speed: `{round(speed, 2)} MB/s`** 🔥\n\n"
            f"💡 _Ye Koyeb server ki max parallel capacity_\n"
            f"🎯 _ADM/IDM se yahi speed milegi (bots ke saath)_"
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{str(e)[:200]}`")

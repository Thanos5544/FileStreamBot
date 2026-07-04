import asyncio
import time
import aiohttp
from pyrogram import filters
from FileStream.bot import FileStream


TEST_URLS = [
    ("Hetzner (Germany)", "https://speed.hetzner.de/100MB.bin"),
    ("OVH (France)", "https://proof.ovh.net/files/100Mb.dat"),
    ("Cachefly (Global)", "https://cachefly.cachefly.net/100mb.test"),
    ("Linode (Global)", "https://speedtest.newark.linode.com/100MB-newark.bin"),
]


@FileStream.on_message(filters.command("speedtest"))
async def speed_test(_, m):
    msg = await m.reply_text("⚡ **Sᴘᴇᴇᴅ Tᴇsᴛ Sᴛᴀʀᴛɪɴɢ...**\n\nTᴇsᴛɪɴɢ ᴍᴜʟᴛɪᴘʟᴇ sᴇʀᴠᴇʀs...")
    
    results = []
    
    for name, url in TEST_URLS:
        try:
            await msg.edit_text(
                f"⚡ **Sᴘᴇᴇᴅ Tᴇsᴛ Rᴜɴɴɪɴɢ**\n\n"
                f"🌐 Tᴇsᴛɪɴɢ: **{name}**\n"
                f"⏳ Pʟᴇᴀsᴇ ᴡᴀɪᴛ..."
            )
            
            start_time = time.time()
            total_bytes = 0
            
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        results.append({
                            "name": name,
                            "error": f"HTTP {resp.status}"
                        })
                        continue
                    
                    async for chunk in resp.content.iter_chunked(1024 * 64):
                        total_bytes += len(chunk)
                        
                        # Stop after 30 sec or 100 MB
                        if time.time() - start_time > 30 or total_bytes > 100 * 1024 * 1024:
                            break
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration < 0.5 or total_bytes < 1024 * 1024:
                results.append({
                    "name": name,
                    "error": "Connection failed"
                })
                continue
            
            size_mb = total_bytes / 1024 / 1024
            speed_mbps = size_mb / duration
            
            results.append({
                "name": name,
                "size": round(size_mb, 2),
                "time": round(duration, 2),
                "speed": round(speed_mbps, 2)
            })
            
        except asyncio.TimeoutError:
            results.append({"name": name, "error": "Timeout"})
        except Exception as e:
            results.append({"name": name, "error": str(e)[:40]})
    
    # Format results
    text = "🚀 **Sᴘᴇᴇᴅ Tᴇsᴛ Rᴇsᴜʟᴛs**\n\n"
    
    max_speed = 0
    working_tests = 0
    
    for r in results:
        if "error" in r:
            text += f"❌ **{r['name']}**\n   └ `{r['error']}`\n\n"
        else:
            text += f"✅ **{r['name']}**\n"
            text += f"   ├ Size: `{r['size']} MB`\n"
            text += f"   ├ Time: `{r['time']} sec`\n"
            text += f"   └ Speed: **`{r['speed']} MB/s`** ⚡\n\n"
            working_tests += 1
            if r['speed'] > max_speed:
                max_speed = r['speed']
    
    text += f"━━━━━━━━━━━━━━━━━━\n"
    
    if working_tests > 0:
        text += f"🏆 **Max Speed: `{max_speed} MB/s`**\n\n"
        text += f"💡 _Ye Kᴏʏᴇʙ ᴋɪ ᴀᴄᴛᴜᴀʟ ᴅᴏᴡɴʟᴏᴀᴅ ᴄᴀᴘᴀᴄɪᴛʏ ʜᴀɪ_"
    else:
        text += f"⚠️ **Sᴀʙ sᴇʀᴠᴇʀs ғᴀɪʟ ʜᴜᴇ**\n"
        text += f"Nᴇᴛᴡᴏʀᴋ ɪssᴜᴇ ʜᴏ sᴀᴋᴛᴀ ʜᴀɪ."
    
    await msg.edit_text(text)

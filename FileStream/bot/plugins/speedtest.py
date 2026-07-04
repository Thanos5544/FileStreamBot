import asyncio
import time
import aiohttp
from pyrogram import filters
from FileStream.bot import FileStream


@FileStream.on_message(filters.command("speedtest"))
async def speed_test(_, m):
    msg = await m.reply_text("⚡ **Sᴘᴇᴇᴅ Tᴇsᴛ Sᴛᴀʀᴛɪɴɢ...**")
    
    url = "https://speed.cloudflare.com/__down?bytes=524288000"  # 500 MB
    
    try:
        start_time = time.time()
        total_bytes = 0
        last_update = time.time()
        max_speed = 0
        speed_samples = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    total_bytes += len(chunk)
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Update every 2 seconds
                    if current_time - last_update >= 2:
                        current_speed = (total_bytes / 1024 / 1024) / elapsed
                        downloaded_mb = round(total_bytes / 1024 / 1024, 2)
                        
                        if current_speed > max_speed:
                            max_speed = current_speed
                        
                        speed_samples.append(current_speed)
                        
                        try:
                            await msg.edit_text(
                                f"⚡ **Lɪᴠᴇ Sᴘᴇᴇᴅ Tᴇsᴛ**\n\n"
                                f"📥 **Downloaded:** `{downloaded_mb} MB`\n"
                                f"⚡ **Current:** `{round(current_speed, 2)} MB/s`\n"
                                f"🏆 **Max:** `{round(max_speed, 2)} MB/s`\n"
                                f"⏱ **Time:** `{round(elapsed, 1)} sec`\n\n"
                                f"⏳ _Tᴇsᴛɪɴɢ..._"
                            )
                        except:
                            pass
                        
                        last_update = current_time
                        
                        # Stop after 30 sec or 500 MB
                        if elapsed > 30 or total_bytes > 500 * 1024 * 1024:
                            break
        
        total_time = time.time() - start_time
        avg_speed = sum(speed_samples) / len(speed_samples) if speed_samples else 0
        
        # Final result
        await msg.edit_text(
            f"🚀 **Sᴘᴇᴇᴅ Tᴇsᴛ Cᴏᴍᴘʟᴇᴛᴇ**\n\n"
            f"📥 **Downloaded:** `{round(total_bytes / 1024 / 1024, 2)} MB`\n"
            f"⏱ **Duration:** `{round(total_time, 2)} sec`\n\n"
            f"⚡ **Average Speed:** `{round(avg_speed, 2)} MB/s`\n"
            f"🏆 **Max Speed:** **`{round(max_speed, 2)} MB/s`**\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 _Ye Koyeb sᴇʀᴠᴇʀ ᴋɪ ᴀᴄᴛᴜᴀʟ ᴄᴀᴘᴀᴄɪᴛʏ ʜᴀɪ_\n"
            f"🌐 _Test Server: Cloudflare Global CDN_"
        )
        
    except asyncio.TimeoutError:
        await msg.edit_text("❌ **Test Timeout** - Server slow ho sakta hai")
    except Exception as e:
        await msg.edit_text(f"❌ **Error:**\n`{str(e)[:200]}`")

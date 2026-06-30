import asyncio
import time
import platform
import psutil
from pyrogram import filters
from FileStream.bot import FileStream
from FileStream import StartTime


@FileStream.on_message(filters.command("system"))
async def system_info(_, m):

    start = time.time()

    msg = await m.reply_text(
        "⚡ Sʏsᴛᴇᴍ Cʜᴇᴄᴋɪɴɢ..."
    )

    ping = round((time.time() - start) * 1000, 2)

    uptime = int(time.time() - StartTime)
    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    minutes = (uptime % 3600) // 60

    cpu = psutil.cpu_percent()
    cores = psutil.cpu_count()

    ram = psutil.virtual_memory()
    ram_used = round(ram.used / 1024**2)
    ram_total = round(ram.total / 1024**2)

    disk = psutil.disk_usage("/")
    disk_used = round(disk.used / 1024**2)
    disk_total = round(disk.total / 1024**2)

    os = platform.system()

    await msg.edit_text(
f"""**⚙️ Sʏsᴛᴇᴍ Iɴғᴏ**

🐧 **OS:** `{os}`
🏓 **Pɪɴɢ:** `{ping} ms`
⏱️ **Uᴘᴛɪᴍᴇ:** `{days}d {hours}h {minutes}m`
🖥️ **CPU:** `{cpu}% | {cores} Cᴏʀᴇs`
💾 **RAM:** `{ram_used} MB / {ram_total} MB`
📦 **Dɪsᴋ:** `{disk_used} MB / {disk_total} MB`
🚀 **Sᴛᴀᴛᴜs:** `Oɴʟɪɴᴇ`

⚡ **Sᴇʀᴠᴇʀ Rᴜɴɴɪɴɢ Sᴍᴏᴏᴛʜʟʏ 🔥**"""
    )

    await asyncio.sleep(30)
    await msg.delete()

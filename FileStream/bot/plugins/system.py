import asyncio
import time
import platform
import psutil
import os
from pyrogram import filters
from FileStream.bot import FileStream, multi_clients, work_loads
from FileStream import StartTime


def get_folder_size(path):
    """Ek folder ka total size return karta hai (MB mein)"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except:
                pass
    return round(total_size / 1024**2, 2)


@FileStream.on_message(filters.command("system"))
async def system_info(_, m):

    start = time.time()

    msg = await m.reply_text(
        "⚡ Sʏsᴛᴇᴍ Cʜᴇᴄᴋɪɴɢ..."
    )

    ping = round((time.time() - start) * 1000, 2)

    # Uptime
    uptime = int(time.time() - StartTime)
    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    minutes = (uptime % 3600) // 60

    # CPU
    cpu = psutil.cpu_percent()
    cores = psutil.cpu_count()

    # RAM
    ram = psutil.virtual_memory()
    ram_used = round(ram.used / 1024**2)
    ram_total = round(ram.total / 1024**2)
    ram_percent = round((ram.used / ram.total) * 100, 1)

    # Disk (Total System)
    disk = psutil.disk_usage("/")
    disk_used = round(disk.used / 1024**3, 2)
    disk_total = round(disk.total / 1024**3, 2)
    disk_percent = round((disk.used / disk.total) * 100, 1)

    # Bot Files Size
    try:
        bot_size = get_folder_size("FileStream")
    except:
        bot_size = 0

    # OS
    os_name = platform.system()

    # Multi-Bots Info
    total_bots = len(multi_clients)
    total_load = sum(work_loads.values())

    # Load status
    if total_load == 0:
        load_status = "🟢 Iᴅʟᴇ"
    elif total_load <= 3:
        load_status = "🟡 Aᴄᴛɪᴠᴇ"
    else:
        load_status = "🔴 Bᴜsʏ"

    await msg.edit_text(
f"""**⚙️ Sʏsᴛᴇᴍ Iɴғᴏ**

🐧 **OS:** `{os_name}`
🏓 **Pɪɴɢ:** `{ping} ms`
⏱️ **Uᴘᴛɪᴍᴇ:** `{days}d {hours}h {minutes}m`

**💻 Hᴀʀᴅᴡᴀʀᴇ**
🖥️ **CPU:** `{cpu}% | {cores} Cᴏʀᴇs`
💾 **RAM:** `{ram_used} MB / {ram_total} MB ({ram_percent}%)`
📦 **Dɪsᴋ:** `{disk_used} GB / {disk_total} GB ({disk_percent}%)`
🤖 **Bᴏᴛ Sɪᴢᴇ:** `{bot_size} MB`

**🚀 Mᴜʟᴛɪ-Cʟɪᴇɴᴛ**
🤖 **Aᴄᴛɪᴠᴇ Bᴏᴛs:** `{total_bots}`
📊 **Cᴜʀʀᴇɴᴛ Lᴏᴀᴅ:** `{total_load}`
⚡ **Sᴛᴀᴛᴜs:** {load_status}

🌟 **Sᴇʀᴠᴇʀ Rᴜɴɴɪɴɢ Sᴍᴏᴏᴛʜʟʏ 🔥**"""
    )

    await asyncio.sleep(30)
    await msg.delete()

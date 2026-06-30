import asyncio
import time
import platform
import psutil
from pyrogram import filters
from FileStream.bot import FileStream, StartTime


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
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    os = platform.system()
    release = platform.release()

    await msg.edit_text(
f"""⚙️ **Sʏsᴛᴇᴍ Iɴғᴏ**

🐧 **OS:**
`{os} {release}`

🏓 **Pɪɴɢ:**
`{ping} ms`

⏱️ **Uᴘᴛɪᴍᴇ:**
`{days}d {hours}h {minutes}m`

🖥️ **CPU:**
`{cpu}%`

💾 **RAM:**
`{ram}%`

📦 **Dɪsᴋ:**
`{disk}%`

🚀 **Sᴛᴀᴛᴜs:**
`Oɴʟɪɴᴇ`

⚡ **Nᴏᴛᴇ:**
Lᴏᴡ Pɪɴɢ = Fᴀsᴛ Rᴇsᴘᴏɴsᴇ

Sᴇʀᴠᴇʀ Rᴜɴɴɪɴɢ Sᴍᴏᴏᴛʜʟʏ 🔥"""
    )

    await asyncio.sleep(30)
    await msg.delete()

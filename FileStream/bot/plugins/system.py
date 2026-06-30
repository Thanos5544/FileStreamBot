import time
import platform
import psutil
import asyncio
from pyrogram import Client, filters


START_TIME = time.time()


def uptime():
    sec = int(time.time() - START_TIME)
    return f"{sec//3600}h {(sec%3600)//60}m {sec%60}s"


def system_uptime():
    sec = int(time.time() - psutil.boot_time())
    return f"{sec//3600}h {(sec%3600)//60}m {sec%60}s"


@Client.on_message(filters.command("system"))
async def system(_, message):

    start = time.time()

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    latency = (time.time() - start) * 1000

    msg = await message.reply(
f"""💻 **System Information**

🖥️ OS: `{platform.system()}`

⏰ Bot Uptime: `{uptime()}`

🔄 System Uptime: `{system_uptime()}`

💾 RAM Usage:
`{ram.used/1024/1024:.2f} MB / {ram.total/1024/1024:.2f} MB`

📁 Disk Usage:
`{disk.used/1024/1024/1024:.2f} GB / {disk.total/1024/1024/1024:.2f} GB`

📶 Latency:
`{latency:.3f} ms`
"""
)

    await asyncio.sleep(30)
    await msg.delete()

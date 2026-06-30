import time
import asyncio
from pyrogram import Client, filters


@Client.on_message(filters.command("ping"))
async def ping(_, message):

    start = time.time()

    msg = await message.reply("🏓 Checking...")

    ms = (time.time() - start) * 1000

    await msg.edit(
        f"🏓 **Ping!** : `{ms:.3f} ms`"
    )

    await asyncio.sleep(30)
    await msg.delete()

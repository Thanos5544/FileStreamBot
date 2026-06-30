import asyncio
import speedtest
from pyrogram import filters
from FileStream.bot import FileStream


@FileStream.on_message(filters.command("speed"))
async def speed_test(_, m):

    msg = await m.reply_text(
        "🚀 Sᴘᴇᴇᴅ Tᴇsᴛ Sᴛᴀʀᴛɪɴɢ..."
    )

    try:
        st = speedtest.Speedtest()
        st.get_best_server()

        download = st.download() / 1024 / 1024
        upload = st.upload() / 1024 / 1024

        chrome_speed = download / 8

        await msg.edit_text(
f"""🚀 **Sᴇʀᴠᴇʀ Sᴘᴇᴇᴅ Tᴇsᴛ**

⬇️ **Dᴏᴡɴʟᴏᴀᴅ Sᴘᴇᴇᴅ:**
`{download:.2f} Mbps`

⬆️ **Uᴘʟᴏᴀᴅ Sᴘᴇᴇᴅ:**
`{upload:.2f} Mbps`

📦 **Aᴘᴘʀᴏx Cʜʀᴏᴍᴇ Dᴏᴡɴʟᴏᴀᴅ:**
`{chrome_speed:.2f} MB/s`

⚡ **Nᴏᴛᴇ:**
Tʜɪs ɪs sᴇʀᴠᴇʀ ɴᴇᴛᴡᴏʀᴋ sᴘᴇᴇᴅ.

Iғ Cʜʀᴏᴍᴇ Dᴏᴡɴʟᴏᴀᴅ sᴘᴇᴇᴅ ɪs sʟᴏᴡ:
• Tʀʏ ADM Dᴏᴡɴʟᴏᴀᴅᴇʀ ғᴏʀ Bᴇᴛᴛᴇʀ Sᴘᴇᴇᴅ
• Aᴄᴛᴜᴀʟ sᴘᴇᴇᴅ ᴅᴇᴘᴇɴᴅs ᴏɴ ɪɴᴛᴇʀɴᴇᴛ & Tᴇʟᴇɢʀᴀᴍ

📌 1 Mbps ≈ 0.125 MB/s"""
        )

        await asyncio.sleep(30)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(
            f"❌ Sᴘᴇᴇᴅ Tᴇsᴛ Fᴀɪʟᴇᴅ\n\n`{e}`"
        )
        await asyncio.sleep(30)
        await msg.delete()

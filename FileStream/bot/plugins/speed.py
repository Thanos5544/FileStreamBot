import asyncio
import speedtest
from pyrogram import filters
from FileStream.bot import FileStream


@FileStream.on_message(filters.command("speed"))
async def speed_test(_, m):

    msg = await m.reply_text(
        "⚡ Sᴘᴇᴇᴅ Cʜᴇᴄᴋɪɴɢ..."
    )

    try:
        st = speedtest.Speedtest()
        st.get_best_server()

        download = st.download() / 1024 / 1024
        upload = st.upload() / 1024 / 1024

        await msg.edit_text(
f"""**🚀 Sᴘᴇᴇᴅ Tᴇsᴛ**

⚡ **Sᴇʀᴠᴇʀ Nᴇᴛᴡᴏʀᴋ Sᴘᴇᴇᴅ**

⬇️ **Dᴏᴡɴʟᴏᴀᴅ:** `{download:.2f} Mbps`
⬆️ **Uᴘʟᴏᴀᴅ:** `{upload:.2f} Mbps`

📌 **Nᴏᴛᴇ:**
**Iғ Cʜʀᴏᴍᴇ Sᴘᴇᴇᴅ ɪs Sʟᴏᴡ:**
• **Tʀʏ ADM Dᴏᴡɴʟᴏᴀᴅᴇʀ ғᴏʀ Bᴇᴛᴛᴇʀ Sᴘᴇᴇᴅ**
• **Sᴘᴇᴇᴅ Dᴇᴘᴇɴᴅs Oɴ Nᴇᴛᴡᴏʀᴋ**

🔥 **Sᴇʀᴠᴇʀ Rᴜɴɴɪɴɢ Sᴍᴏᴏᴛʜʟʏ**
"""
        )

    except Exception as e:
        await msg.edit_text(
            f"❌ **Sᴘᴇᴇᴅ Fᴀɪʟᴇᴅ**\n`{e}`"
        )

    await asyncio.sleep(30)
    await msg.delete()

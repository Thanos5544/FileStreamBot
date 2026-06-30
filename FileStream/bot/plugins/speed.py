import speedtest
import asyncio
from pyrogram import Client, filters


@Client.on_message(filters.command("speed"))
async def speed(_, message):

    msg = await message.reply(
        "🚀 Speed test running... Please wait."
    )

    try:
        st = speedtest.Speedtest()

        st.get_best_server()

        download = st.download() / 1024 / 1024
        upload = st.upload() / 1024 / 1024

        await msg.edit(
f"""🚀 **Server Speed Test**

⬇️ Download Speed:
`{download:.2f} Mbps`

⬆️ Upload Speed:
`{upload:.2f} Mbps`

📦 Approx Chrome Download:
`{download/8:.2f} MB/s`


⚡ **Note:**
This is the server network speed.

Actual Chrome download speed may vary depending on:
• Your internet connection
• Telegram speed
• Server load

📌 1 Mbps ≈ 0.125 MB/s
"""
)

    except Exception as e:
        await msg.edit(f"❌ Speed test failed\n`{e}`")


    await asyncio.sleep(30)
    await msg.delete()

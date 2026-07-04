from pyrogram import Client, filters
from pyrogram.types import Message
from FileStream.bot import multi_clients, work_loads
from FileStream.config import Telegram


@Client.on_message(filters.command("check") & filters.private)
async def check_multi_bots(client, message: Message):
    total = len(multi_clients)
    text = f"🔍 **Multi-Client Debug Info**\n\n"
    text += f"📊 Total Clients Loaded: **{total}**\n"
    text += f"🔧 Multi-Client Enabled: **{Telegram.MULTI_CLIENT}**\n\n"
    text += f"**Loaded Clients:**\n"
    
    for client_id, client_obj in multi_clients.items():
        try:
            me = await client_obj.get_me()
            text += f"• Client `{client_id}` → @{me.username} ✅\n"
        except Exception as e:
            text += f"• Client `{client_id}` → ❌ Error: {str(e)[:50]}\n"
    
    text += f"\n**Work Loads:**\n"
    for client_id, load in work_loads.items():
        text += f"• Client `{client_id}` → Load: {load}\n"
    
    await message.reply_text(text)

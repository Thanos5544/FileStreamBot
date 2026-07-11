from pyrogram import filters
from FileStream.bot import FileStream
from FileStream.config import Telegram
from FileStream.utils.database import Database

db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)


# ✅ Jab bot group/channel mein add ho ya message aaye
# Mongo mein save + ULOG_CHANNEL mein log
@FileStream.on_message(filters.group | filters.channel)
async def gc_auto_save(client, message):
    chat = message.chat

    if chat.type not in ("group", "supergroup", "channel"):
        return

    gtype = "channel" if chat.type == "channel" else "group"

    # ✅ MongoDB save (upsert)
    await db.col.update_one(
        {"id": chat.id},
        {
            "$set": {
                "id": chat.id,
                "name": chat.title,
                "username": chat.username if chat.username else None,
                "type": gtype,
                "last_seen": message.date
            }
        },
        upsert=True
    )

    # ✅ Pehli baar detect hua toh log bhej
    existing = await db.col.find_one({"id": chat.id})
    if existing and existing.get("logged") is not True:
        await db.col.update_one({"id": chat.id}, {"$set": {"logged": True}})

        try:
            members = await client.get_chat_members_count(chat.id)
        except Exception:
            members = 0

        await client.send_message(
            Telegram.ULOG_CHANNEL,
            f"**#NEW_{gtype.upper()}**\n"
            f"**Name:** `{chat.title}`\n"
            f"**ID:** `{chat.id}`\n"
            f"**Username:** @{chat.username if chat.username else 'N/A'}\n"
            f"**Members:** `{members}`"
        )


# ✅ /stats command
@FileStream.on_message(filters.command("stats") & filters.user(Telegram.OWNER_ID))
async def bot_stats(_, m):
    users = await db.col.count_documents({"type": "user"})
    groups = await db.col.count_documents({"type": "group"})
    channels = await db.col.count_documents({"type": "channel"})
    files = await db.file.count_documents({})

    await m.reply_text(
        f"**BOT STATS**\n\n"
        f"Users : `{users}`\n"
        f"Groups : `{groups}`\n"
        f"Channels : `{channels}`\n"
        f"Files : `{files}`"
    )


# ✅ /gccast command (sirf group + channel)
@FileStream.on_message(filters.command("gccast") & filters.user(Telegram.OWNER_ID))
async def gccast(_, m):
    if not m.reply_to_message:
        return await m.reply_text("Reply to a message first")

    msg = m.reply_to_message
    done = 0

    async for u in db.col.find({"type": {"$in": ["group", "channel"]}}):
        try:
            await msg.copy(u["id"])
            done += 1
        except Exception:
            pass

    await m.reply_text(f"**GCCast Done ✅**\nSent to: `{done}` GC")

from pyrogram import filters
from pyrogram.types import (
    ChatMemberUpdated,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)
from pyrogram.enums import ChatMemberStatus

from FileStream.bot import FileStream
from FileStream.config import Telegram
from FileStream.utils.database import Database
from FileStream.utils.broadcast_helper import send_msg

db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)

# -------------------- GROUP / CHANNEL SAVE -------------------- #

@FileStream.on_chat_member_updated()
async def gc_save(client, member: ChatMemberUpdated):
    chat = member.chat

    if chat.type not in ("group", "supergroup", "channel"):
        return

    if (
        member.new_chat_member
        and member.new_chat_member.status == ChatMemberStatus.MEMBER
    ):
        gtype = "channel" if chat.type == "channel" else "group"
        await db.add_user(chat.id, gtype)

        try:
            members = await client.get_chat_members_count(chat.id)
        except Exception:
            members = 0

        await client.send_message(
            Telegram.ULOG_CHANNEL,
            f"**#NEW_{gtype.upper()}**\n"
            f"Name: `{chat.title}`\n"
            f"ID: `{chat.id}`\n"
            f"Members: `{members}`"
        )

    elif (
        member.old_chat_member
        and member.old_chat_member.status == ChatMemberStatus.MEMBER
        and member.new_chat_member.status == ChatMemberStatus.LEFT
    ):
        await db.col.delete_one({"id": chat.id})
        await client.send_message(
            Telegram.ULOG_CHANNEL,
            f"**#LEFT_{chat.type.upper()}**\nID: `{chat.id}`"
        )


# -------------------- /stats -------------------- #

@FileStream.on_message(filters.command("stats") & filters.user(Telegram.OWNER_ID))
async def stats_cmd(_, m: Message):
    users = await db.total_users_count()
    groups = await db.total_groups_count()
    channels = await db.total_channels_count()
    links = await db.total_files()

    await m.reply_text(
        f"**BOT STATS**\n\n"
        f"Users : `{users}`\n"
        f"Groups : `{groups}`\n"
        f"Channels : `{channels}`\n"
        f"Total Links : `{links}`"
    )


# -------------------- /gccast -------------------- #

@FileStream.on_message(filters.command("gccast") & filters.user(Telegram.OWNER_ID))
async def gccast(_, m: Message):
    if not m.reply_to_message:
        return await m.reply_text("**Reply to a message for GCCast**")

    msg = m.reply_to_message
    done = 0

    async for u in db.get_all_by_type("group"):
        code, _ = await send_msg(_, u["id"], msg)
        if code == 200:
            done += 1

    async for u in db.get_all_by_type("channel"):
        code, _ = await send_msg(_, u["id"], msg)
        if code == 200:
            done += 1

    await m.reply_text(f"**GCCast Done ✅**\nSent to: `{done}` Groups/Channels")

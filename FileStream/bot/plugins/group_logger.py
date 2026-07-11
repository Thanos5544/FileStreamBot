from pyrogram import filters
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus

from FileStream.bot import FileStream
from FileStream.config import Telegram
from FileStream.utils.database import db


@FileStream.on_chat_member_updated()
async def grp_log(client, member: ChatMemberUpdated):
    chat = member.chat
    if chat.type not in ("group", "supergroup", "channel"):
        return

    if member.new_chat_member and member.new_chat_member.status == ChatMemberStatus.MEMBER:
        t = "channel" if chat.type == "channel" else "group"
        await db.add_user(chat.id, t)

        try:
            members = await client.get_chat_members_count(chat.id)
        except Exception:
            members = 0

        await client.send_message(
            Telegram.ULOG_CHANNEL,
            f"#NEW_{t.upper()}\nName: {chat.title}\nID: `{chat.id}`\nMembers: {members}"
        )

    elif member.old_chat_member and member.new_chat_member.status == ChatMemberStatus.LEFT:
        await db.col.delete_one({"id": chat.id})
        await client.send_message(
            Telegram.ULOG_CHANNEL,
            f"#LEFT_{chat.type.upper()}\nID: `{chat.id}`"
        )

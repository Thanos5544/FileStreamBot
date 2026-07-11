from pyrogram import filters
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus

from FileStream import FileStream
from FileStream.config import Telegram
from FileStream.utils.database import Database

db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)


@FileStream.on_chat_member_updated()
async def group_add_remove_logger(client, member: ChatMemberUpdated):
    chat = member.chat

    if chat.type not in ("group", "supergroup", "channel"):
        return

    # Bot added
    if (
        member.new_chat_member
        and member.new_chat_member.status == ChatMemberStatus.MEMBER
        and member.old_chat_member is None
    ) or (
        member.new_chat_member
        and member.new_chat_member.status == ChatMemberStatus.MEMBER
        and member.old_chat_member.status != ChatMemberStatus.MEMBER
    ):
        added_by = member.from_user

        data = {
            "id": chat.id,
            "name": chat.title,
            "username": chat.username if chat.username else None,
            "type": "channel" if chat.type == "channel" else "group",
            "added_by": added_by.id if added_by else None
        }

        await db.col.update_one(
            {"id": chat.id},
            {"$set": data},
            upsert=True
        )

        try:
            members = await client.get_chat_members_count(chat.id)
        except Exception:
            members = 0

        adder = f"[{added_by.first_name}](tg://user?id={added_by.id})" if added_by else "Unknown"
        adder_id = f"`{added_by.id}`" if added_by else "N/A"

        await client.send_message(
            Telegram.ULOG_CHANNEL,
            f"**#NEW_{data['type'].upper()}**\n\n"
            f"**Name:** `{chat.title}`\n"
            f"**ID:** `{chat.id}`\n"
            f"**Username:** @{chat.username if chat.username else 'N/A'}\n"
            f"**Members:** `{members}`\n"
            f"**Added By:** {adder}\n"
            f"**Adder ID:** {adder_id}"
        )

    # Bot removed
    elif (
        member.old_chat_member
        and member.old_chat_member.status == ChatMemberStatus.MEMBER
        and member.new_chat_member.status == ChatMemberStatus.LEFT
    ):
        await db.col.delete_one({"id": chat.id})

        await client.send_message(
            Telegram.ULOG_CHANNEL,
            f"**#LEFT_{chat.type.upper()}**\n\n"
            f"**ID:** `{chat.id}`\n"
            f"**Name:** `{chat.title}`"
        )

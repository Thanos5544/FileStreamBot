import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.bot import FileStream
from FileStream.config import Telegram
from FileStream.utils.database import db
from FileStream.utils.broadcast_helper import send_msg

pin = {"on": False}


@FileStream.on_message(filters.command("status") & filters.user(Telegram.OWNER_ID))
async def sts(_, m):
    u = await db.total_users_count()
    g = await db.total_groups_count()
    c = await db.total_channels_count()
    f = await db.total_files()
    await m.reply(f"Users: {u}\nGroups: {g}\nChannels: {c}\nFiles: {f}")


@FileStream.on_message(filters.command("broadcast") & filters.user(Telegram.OWNER_ID))
async def bcast_menu(_, m):
    await m.reply(
        "Select Target",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Users", "b_user")],
            [InlineKeyboardButton("Groups", "b_group")],
            [InlineKeyboardButton("Channels", "b_channel")],
            [InlineKeyboardButton("All", "b_all")],
            [
                InlineKeyboardButton("Pin OFF", "pin_off"),
                InlineKeyboardButton("Pin ON", "pin_on")
            ]
        ])
    )


@FileStream.on_callback_query(filters.user(Telegram.OWNER_ID))
async def bcast_cb(client, query):
    d = query.data

    if d == "pin_on":
        pin["on"] = True
        return await query.answer("Pin ON")
    if d == "pin_off":
        pin["on"] = False
        return await query.answer("Pin OFF")

    if not query.message.reply_to_message:
        return await query.answer("Reply to message first", show_alert=True)

    target = d.replace("b_", "")
    msg = query.message.reply_to_message
    done = 0

    users = db.get_all_users() if target == "all" else db.get_all_by_type(target)
    async for u in users:
        code, _ = await send_msg(client, u["id"], msg, pin["on"])
        if code == 200:
            done += 1

    await query.message.edit_text(f"Done: {done}")

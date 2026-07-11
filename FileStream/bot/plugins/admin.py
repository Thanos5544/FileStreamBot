import os
import time
import string
import random
import asyncio
import aiofiles
import datetime

from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums.parse_mode import ParseMode

from FileStream.bot import FileStream
from FileStream.config import Telegram
from FileStream.server.exceptions import FIleNotFound
from FileStream.utils.database import Database
from FileStream.utils.broadcast_helper import send_msg

db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)
pin_status = {"enabled": False}


# --------------------- STATUS --------------------- #
@FileStream.on_message(filters.command("status") & filters.user(Telegram.OWNER_ID))
async def sts(c: Client, m: Message):
    users = await db.total_users_count()
    groups = await db.total_groups_count()
    channels = await db.total_channels_count()
    links = await db.total_files()

    await m.reply_text(
        f"**BOT STATUS**\n\n"
        f"Users : `{users}`\n"
        f"Groups : `{groups}`\n"
        f"Channels : `{channels}`\n"
        f"Links : `{links}`"
    )


# --------------------- BAN --------------------- #
@FileStream.on_message(filters.command("ban") & filters.user(Telegram.OWNER_ID))
async def ban_user(b, m: Message):
    uid = m.text.split("/ban ")[-1]
    if not await db.is_user_banned(int(uid)):
        await db.ban_user(int(uid))
        await db.delete_user(int(uid))
        await m.reply_text(f"`{uid}` **banned**")
    else:
        await m.reply_text(f"`{uid}` **already banned**")


# --------------------- UNBAN --------------------- #
@FileStream.on_message(filters.command("unban") & filters.user(Telegram.OWNER_ID))
async def unban_user(b, m: Message):
    uid = m.text.split("/unban ")[-1]
    if await db.is_user_banned(int(uid)):
        await db.unban_user(int(uid))
        await m.reply_text(f"`{uid}` **unbanned**")
    else:
        await m.reply_text(f"`{uid}` **not banned**")


# --------------------- BROADCAST MENU --------------------- #
@FileStream.on_message(filters.command("broadcast") & filters.user(Telegram.OWNER_ID))
async def broadcast_menu(c, m: Message):
    await m.reply_text(
        "**Select Broadcast Target**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Users", callback_data="b_users")],
            [InlineKeyboardButton("Groups", callback_data="b_groups")],
            [InlineKeyboardButton("Channels", callback_data="b_channels")],
            [InlineKeyboardButton("All", callback_data="b_all")],
            [
                InlineKeyboardButton("Pin: OFF", callback_data="pin_off"),
                InlineKeyboardButton("Pin: ON", callback_data="pin_on")
            ]
        ])
    )


# --------------------- BROADCAST CALLBACK --------------------- #
@FileStream.on_callback_query(filters.user(Telegram.OWNER_ID))
async def broadcast_callbacks(c, query):
    data = query.data

    if data == "pin_off":
        pin_status["enabled"] = False
        return await query.answer("Pin Disabled")

    if data == "pin_on":
        pin_status["enabled"] = True
        return await query.answer("Pin Enabled")

    if not query.message.reply_to_message:
        return await query.answer("Reply to a message first", show_alert=True)

    msg = query.message.reply_to_message
    target = data.replace("b_", "")

    done = 0
    async for u in db.get_all_by_type(target) if target != "all" else db.get_all_users():
        code, _ = await send_msg(c, u["id"], msg, pin_status["enabled"])
        if code == 200:
            done += 1

    await query.message.edit_text(
        f"✅ Broadcast Done\nTarget: `{target}`\nSent: `{done}`"
    )


# --------------------- DELETE FILE --------------------- #
@FileStream.on_message(filters.command("del") & filters.user(Telegram.OWNER_ID))
async def del_file(c: Client, m: Message):
    fid = m.text.split(" ")[-1]
    try:
        info = await db.get_file(fid)
    except FIleNotFound:
        return await m.reply_text("File already deleted")

    await db.delete_one_file(info['_id'])
    await db.count_links(info['user_id'], "-")
    await m.reply_text("File Deleted ✅")


# --------------------- DELETE ALL --------------------- #
async def clear_all_files():
    await db.file.delete_many({})
    await db.col.update_many({}, {"$set": {"Links": 0}})


@FileStream.on_message(filters.command("delete") & filters.user(Telegram.OWNER_ID))
async def delete_all(_, m: Message):
    await clear_all_files()
    await m.reply_text("✅ All Files Deleted")


# --------------------- AUTO DELETE --------------------- #
async def auto_delete_loop():
    while True:
        await asyncio.sleep(86400)
        await clear_all_files()


asyncio.create_task(auto_delete_loop())

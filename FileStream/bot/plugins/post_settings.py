from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from FileStream.bot.plugins.movie_post import (
    USER_SETTINGS, get_user_settings,
    DEFAULT_BRANDING, DEFAULT_CHANNEL,
    DEFAULT_CAPTION, DEFAULT_BUTTONS, cb_starts,
)

WAITING_INPUT = {}


@Client.on_message(filters.command(["postsettings"]))
async def settings_handler(client, message):
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    
    btns_text = ""
    for i, btn in enumerate(settings.get("buttons", DEFAULT_BUTTONS), 1):
        btns_text += f"  {i}. <code>{btn['text']}</code>\n"
    
    text = (
        "⚙️ <b>Movie Post Settings</b>\n\n"
        f"<b>📢 Channel:</b> <code>{settings.get('channel', DEFAULT_CHANNEL)}</code>\n"
        f"<b>🏷 Branding:</b> <code>{settings['branding']}</code>\n\n"
        f"<b>🔘 Download Buttons:</b>\n{btns_text}\n"
        f"<b>📝 Caption:</b>\n<pre>{settings['caption']}</pre>\n\n"
        "🎯 <b>Choose what to edit:</b>"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Caption", callback_data="setedit|caption"),
         InlineKeyboardButton("🔘 Buttons", callback_data="setedit|buttons")],
        [InlineKeyboardButton("🏷 Branding", callback_data="setedit|branding"),
         InlineKeyboardButton("📢 Channel", callback_data="setedit|channel")],
        [InlineKeyboardButton("↩️ Reset All", callback_data="setedit|reset"),
         InlineKeyboardButton("❌ Close", callback_data="setedit|close")],
    ])
    
    await message.reply_text(text, reply_markup=buttons, parse_mode=ParseMode.HTML)


@Client.on_callback_query(cb_starts("setedit|"), group=-999)
async def settings_callback(client, query):
    try:
        try:
            _, action = query.data.split("|")
        except:
            await query.answer("Invalid", show_alert=True)
            return
        
        user_id = query.from_user.id
        
        if action == "close":
            await query.answer("Closed")
            await query.message.delete()
            return
        
        if action == "reset":
            USER_SETTINGS[user_id] = {
                "branding": DEFAULT_BRANDING,
                "channel": DEFAULT_CHANNEL,
                "caption": DEFAULT_CAPTION,
                "buttons": DEFAULT_BUTTONS.copy(),
            }
            await query.answer("✅ Reset done!", show_alert=True)
            await query.message.delete()
            return
        
        prompts = {
            "caption": (
                "📝 <b>Send New Caption</b>\n\n"
                "<b>Variables:</b>\n"
                "<code>{title}</code> - Title\n"
                "<code>{year}</code> - Year\n"
                "<code>{genres}</code> - Genres\n"
                "<code>{audio}</code> - Audio\n"
                "<code>{quality}</code> - Quality\n"
                "<code>{rating}</code> - Rating\n"
                "<code>{overview}</code> - Story\n\n"
                "Send template or /cancel"
            ),
            "buttons": (
                "🔘 <b>Set Download Buttons</b>\n\n"
                "Format:\n"
                "<code>Button Text | URL</code>\n\n"
                "<b>Multiple buttons (new line each):</b>\n\n"
                "<code>🔽 480p | https://link1.com\n"
                "🔽 720p | https://link2.com\n"
                "🔽 1080p | https://link3.com\n"
                "📢 Channel | https://t.me/ch</code>\n\n"
                "Send buttons or /cancel"
            ),
            "branding": (
                "🏷 <b>Send Branding</b>\n\n"
                "Watermark on poster\n\n"
                "Example: <code>@YourChannel</code>\n\n"
                "Send or /cancel"
            ),
            "channel": (
                "📢 <b>Send Channel</b>\n\n"
                "Top-left on poster\n\n"
                "Example: <code>@YourChannel</code>\n\n"
                "Send or /cancel"
            ),
        }
        
        if action in prompts:
            WAITING_INPUT[user_id] = action
            await query.answer()
            await query.message.edit_text(prompts[action], parse_mode=ParseMode.HTML)
    
    finally:
        raise StopPropagation


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client, message):
    user_id = message.from_user.id
    if user_id in WAITING_INPUT:
        WAITING_INPUT.pop(user_id)
        await message.reply_text("❌ <b>Cancelled</b>")


@Client.on_message(filters.text & filters.private & ~filters.command([
    "start", "help", "movie", "post", "tv", "img", "settings",
    "postsettings", "cancel", "system", "check", "yt", "ytdl",
    "song", "music", "mp3"
]))
async def handle_input(client, message):
    user_id = message.from_user.id
    
    if user_id not in WAITING_INPUT:
        return
    
    input_type = WAITING_INPUT.pop(user_id)
    text = message.text.strip()
    settings = get_user_settings(user_id)
    
    if input_type == "caption":
        settings["caption"] = text
        await message.reply_text(
            f"✅ <b>Caption updated!</b>\n\n<pre>{text}</pre>",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "buttons":
        new_buttons = []
        for line in text.split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                bt = parts[0].strip()
                bu = parts[1].strip()
                if bt and bu and bu.startswith(("http://", "https://", "tg://", "t.me/")):
                    new_buttons.append({"text": bt, "url": bu})
        
        if not new_buttons:
            return await message.reply_text(
                "❌ <b>Invalid format!</b>\n\nUse: <code>Text | URL</code>",
                parse_mode=ParseMode.HTML
            )
        
        settings["buttons"] = new_buttons
        preview = "\n".join([f"• {b['text']}" for b in new_buttons])
        
        await message.reply_text(
            f"✅ <b>Buttons updated!</b> ({len(new_buttons)})\n\n<pre>{preview}</pre>",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "branding":
        settings["branding"] = text
        await message.reply_text(
            f"✅ <b>Branding:</b> <code>{text}</code>",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "channel":
        settings["channel"] = text
        await message.reply_text(
            f"✅ <b>Channel:</b> <code>{text}</code>",
            parse_mode=ParseMode.HTML
        )

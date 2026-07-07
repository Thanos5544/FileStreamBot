from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


from FileStream.bot.plugins.movie_post import (
    USER_SETTINGS,
    get_user_settings,
    DEFAULT_BRANDING,
    DEFAULT_CHANNEL,
    DEFAULT_CAPTION,
    DEFAULT_BUTTON_TEXT,
    DEFAULT_BUTTON_URL,
    cb_starts,
)


WAITING_INPUT = {}


@Client.on_message(filters.command(["postsettings"]))
async def settings_handler(client, message):
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    
    text = (
        "⚙️ <b>Movie Post Settings</b>\n\n"
        f"<b>• Channel:</b> <code>{settings.get('channel', DEFAULT_CHANNEL)}</code>\n"
        f"<b>• Branding:</b> <code>{settings['branding']}</code>\n"
        f"<b>• Button Text:</b> <code>{settings['button_text']}</code>\n"
        f"<b>• Button URL:</b> <code>{settings['button_url']}</code>\n\n"
        f"<b>• Caption Template:</b>\n"
        f"<pre>{settings['caption']}</pre>\n\n"
        "🎯 <b>Choose what to edit:</b>"
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Caption", callback_data="setedit|caption"),
            InlineKeyboardButton("🔘 Button", callback_data="setedit|button"),
        ],
        [
            InlineKeyboardButton("🏷 Branding", callback_data="setedit|branding"),
            InlineKeyboardButton("📢 Channel", callback_data="setedit|channel"),
        ],
        [
            InlineKeyboardButton("🔗 Button URL", callback_data="setedit|url"),
            InlineKeyboardButton("↩️ Reset All", callback_data="setedit|reset"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="setedit|close"),
        ],
    ])
    
    await message.reply_text(
        text,
        reply_markup=buttons,
        parse_mode=ParseMode.HTML
    )


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
                "button_text": DEFAULT_BUTTON_TEXT,
                "button_url": DEFAULT_BUTTON_URL,
            }
            await query.answer("✅ Settings reset to default!", show_alert=True)
            await query.message.delete()
            return
        
        prompts = {
            "caption": (
                "📝 <b>Send New Caption Template</b>\n\n"
                "<b>Available Variables:</b>\n"
                "<code>{title}</code> - Movie title\n"
                "<code>{year}</code> - Release year\n"
                "<code>{genres}</code> - Genres\n"
                "<code>{audio}</code> - Audio info\n"
                "<code>{quality}</code> - Quality info\n"
                "<code>{rating}</code> - IMDB rating\n"
                "<code>{overview}</code> - Plot summary\n\n"
                "<b>HTML Tags:</b>\n"
                "<code>&lt;b&gt;Bold&lt;/b&gt;</code>\n"
                "<code>&lt;i&gt;Italic&lt;/i&gt;</code>\n"
                "<code>&lt;code&gt;Code&lt;/code&gt;</code>\n\n"
                "Send template or /cancel"
            ),
            "button": (
                "🔘 <b>Send Button Text</b>\n\n"
                "Example: <code>🔽 Download</code>\n"
                "Example: <code>📥 Get File</code>\n\n"
                "Send text or /cancel"
            ),
            "url": (
                "🔗 <b>Send Button URL</b>\n\n"
                "Example: <code>https://t.me/YourChannel</code>\n"
                "Example: <code>https://yoursite.com</code>\n\n"
                "Send URL or /cancel"
            ),
            "branding": (
                "🏷 <b>Send Branding Text</b>\n\n"
                "This will appear as watermark\n\n"
                "Example: <code>@YourChannel</code>\n"
                "Example: <code>MyBot 2026</code>\n\n"
                "Send text or /cancel"
            ),
            "channel": (
                "📢 <b>Send Channel Name</b>\n\n"
                "Example: <code>@YourChannel</code>\n\n"
                "Send text or /cancel"
            ),
        }
        
        if action in prompts:
            WAITING_INPUT[user_id] = action
            await query.answer()
            await query.message.edit_text(
                prompts[action],
                parse_mode=ParseMode.HTML
            )
    
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
async def handle_settings_input(client, message):
    user_id = message.from_user.id
    
    if user_id not in WAITING_INPUT:
        return
    
    input_type = WAITING_INPUT.pop(user_id)
    text = message.text.strip()
    
    settings = get_user_settings(user_id)
    
    if input_type == "caption":
        settings["caption"] = text
        await message.reply_text(
            "✅ <b>Caption updated!</b>\n\n"
            f"<pre>{text}</pre>\n\n"
            "Try <code>/movie name</code> to test",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "button":
        settings["button_text"] = text
        await message.reply_text(
            f"✅ <b>Button text updated!</b>\n\n"
            f"New: <code>{text}</code>",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "url":
        if not text.startswith(("http://", "https://", "tg://", "t.me/")):
            return await message.reply_text("❌ <b>Invalid URL</b>")
        settings["button_url"] = text
        await message.reply_text(
            f"✅ <b>Button URL updated!</b>\n\n"
            f"New: <code>{text}</code>",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "branding":
        settings["branding"] = text
        await message.reply_text(
            f"✅ <b>Branding updated!</b>\n\n"
            f"New: <code>{text}</code>",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "channel":
        settings["channel"] = text
        await message.reply_text(
            f"✅ <b>Channel updated!</b>\n\n"
            f"New: <code>{text}</code>",
            parse_mode=ParseMode.HTML
          )

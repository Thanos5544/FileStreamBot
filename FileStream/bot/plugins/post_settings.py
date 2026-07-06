from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


# Import from movie_post
from FileStream.bot.plugins.movie_post import (
    USER_SETTINGS,
    get_user_settings,
    DEFAULT_BRANDING,
    DEFAULT_CAPTION,
    DEFAULT_BUTTON_TEXT,
    DEFAULT_BUTTON_URL,
    cb_starts,
)


# Waiting for input
WAITING_INPUT = {}


@Client.on_message(filters.command(["settings", "postsettings"]))
async def settings_handler(client, message):
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    
    text = (
        "⚙️ **Movie Post Settings**\n\n"
        f"**• Branding:** `{settings['branding']}`\n"
        f"**• Button Text:** `{settings['button_text']}`\n"
        f"**• Button URL:** `{settings['button_url']}`\n\n"
        f"**• Caption Template:**\n"
        f"<pre>{settings['caption']}</pre>\n\n"
        "🎯 **Choose what to edit:**"
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Caption", callback_data=f"setedit|caption"),
            InlineKeyboardButton("🔘 Button", callback_data=f"setedit|button"),
        ],
        [
            InlineKeyboardButton("🏷 Branding", callback_data=f"setedit|branding"),
            InlineKeyboardButton("🔗 Button URL", callback_data=f"setedit|url"),
        ],
        [
            InlineKeyboardButton("↩️ Reset All", callback_data=f"setedit|reset"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data=f"setedit|close"),
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
        except Exception:
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
                "caption": DEFAULT_CAPTION,
                "button_text": DEFAULT_BUTTON_TEXT,
                "button_url": DEFAULT_BUTTON_URL,
                "color": None,
            }
            await query.answer("✅ Settings reset to default!", show_alert=True)
            await query.message.delete()
            return
        
        if action == "caption":
            WAITING_INPUT[user_id] = "caption"
            await query.answer()
            await query.message.edit_text(
                "📝 **Send New Caption Template**\n\n"
                "**Available Variables:**\n"
                "`{title}` - Movie title\n"
                "`{year}` - Release year\n"
                "`{genres}` - Genres\n"
                "`{audio}` - Audio info\n"
                "`{quality}` - Quality info\n"
                "`{rating}` - IMDB rating\n"
                "`{overview}` - Plot summary\n\n"
                "**HTML Tags Supported:**\n"
                "`<b>Bold</b>`\n"
                "`<i>Italic</i>`\n"
                "`<code>Code</code>`\n\n"
                "Send your template now or /cancel"
            )
        
        elif action == "button":
            WAITING_INPUT[user_id] = "button"
            await query.answer()
            await query.message.edit_text(
                "🔘 **Send Button Text**\n\n"
                "Example: `🔽 Download`\n"
                "Example: `📥 Get File`\n\n"
                "Send text or /cancel"
            )
        
        elif action == "url":
            WAITING_INPUT[user_id] = "url"
            await query.answer()
            await query.message.edit_text(
                "🔗 **Send Button URL**\n\n"
                "Example: `https://t.me/YourChannel`\n"
                "Example: `https://yoursite.com`\n\n"
                "Send URL or /cancel"
            )
        
        elif action == "branding":
            WAITING_INPUT[user_id] = "branding"
            await query.answer()
            await query.message.edit_text(
                "🏷 **Send Branding Text**\n\n"
                "This will appear as watermark on poster\n\n"
                "Example: `@YourChannel`\n"
                "Example: `MyBot 2026`\n\n"
                "Send text or /cancel"
            )
    
    finally:
        raise StopPropagation


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client, message):
    user_id = message.from_user.id
    if user_id in WAITING_INPUT:
        WAITING_INPUT.pop(user_id)
        await message.reply_text("❌ **Cancelled**")


@Client.on_message(filters.text & filters.private & ~filters.command(["settings", "cancel", "movie", "post", "tv", "start", "help"]))
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
            "✅ **Caption updated!**\n\n"
            f"<pre>{text}</pre>\n\n"
            "Try `/movie <name>` to test",
            parse_mode=ParseMode.HTML
        )
    
    elif input_type == "button":
        settings["button_text"] = text
        await message.reply_text(
            f"✅ **Button text updated!**\n\n"
            f"New: `{text}`"
        )
    
    elif input_type == "url":
        if not text.startswith(("http://", "https://", "tg://", "t.me/")):
            await message.reply_text("❌ **Invalid URL**")
            return
        settings["button_url"] = text
        await message.reply_text(
            f"✅ **Button URL updated!**\n\n"
            f"New: `{text}`"
        )
    
    elif input_type == "branding":
        settings["branding"] = text
        await message.reply_text(
            f"✅ **Branding updated!**\n\n"
            f"New: `{text}`\n\n"
            f"This will be watermark on posters"
    )

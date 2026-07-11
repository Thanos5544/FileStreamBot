from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.config import Telegram

class LANG(object):

    START_TEXT = """
<b>👋 Hᴇʏ, {}</b>

<b>ᴇᴠᴇʀʏᴛʜɪɴɢ ʏᴏᴜ ɴᴇᴇᴅ ꜰᴏʀ ꜰɪʟᴇ ꜱᴛʀᴇᴀᴍɪɴɢ, ᴅɪʀᴇᴄᴛ ʟɪɴᴋꜱ, ᴄɪɴᴇᴍᴀᴛɪᴄ ᴍᴏᴠɪᴇ ᴘᴏꜱᴛᴇʀꜱ & ᴘʀᴇᴍɪᴜᴍ ᴛʜᴜᴍʙɴᴀɪʟꜱ 🎉</b>

<blockquote>🍁 ᴘᴏᴡᴇʀᴇᴅ ʙʏ : <a href="https://t.me/Patrick_Botz">Pᴀᴛʀɪᴄᴋ Bᴏᴛᴢ</a></blockquote>
"""
    
    HELP_TEXT = """
<b>📖 ʜᴏᴡ ᴛᴏ ᴜꜱᴇ</b>

<b>📂 ꜱᴇɴᴅ ᴀɴʏ ꜰɪʟᴇ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ꜱᴛʀᴇᴀᴍᴀʙʟᴇ &amp; ᴅɪʀᴇᴄᴛ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ.</b>

<b>🎬 /post - ᴄʀᴇᴀᴛᴇ ᴍᴏᴠɪᴇ ᴘᴏꜱᴛᴇʀꜱ.</b>
<b>🖼️ /img - ɢᴇɴᴇʀᴀᴛᴇ ᴍᴏᴠɪᴇ ᴛʜᴜᴍʙɴᴀɪʟꜱ.</b>
<b>🌸 /anime - ᴄʀᴇᴀᴛᴇ ꜱᴛᴜɴɴɪɴɢ ᴀɴɪᴍᴇ ᴘᴏꜱᴛᴇʀꜱ.</b>

<b>⚙️ /settings - ᴄᴏɴꜰɪɢᴜʀᴇ ᴍᴏᴠɪᴇ ᴛʜᴜᴍʙɴᴀɪʟ ꜱᴇᴛᴛɪɴɢꜱ.</b>
<b>🎨 /animesettings - ᴄᴏɴꜰɪɢᴜʀᴇ ᴀɴɪᴍᴇ ᴘᴏꜱᴛᴇʀ ꜱᴇᴛᴛɪɴɢꜱ.</b>

<b>🚫 18+ ᴏʀ ɪʟʟᴇɢᴀʟ ᴄᴏɴᴛᴇɴᴛ ɪꜱ ꜱᴛʀɪᴄᴛʟʏ ᴘʀᴏʜɪʙɪᴛᴇᴅ.</b>

<blockquote>🍁 ɴᴇᴇᴅ ʜᴇʟᴘ? <a href="https://t.me/Patrick_Bateman_r">Pᴀᴛʀɪᴄᴋ Bᴀᴛᴇᴍᴀɴ</a></blockquote>
"""

    ABOUT_TEXT = """
<b>‣ ᴍʏ ɴᴀᴍᴇ : {}</b>
<b>‣ ᴍʏ ʙᴇsᴛ ғʀɪᴇɴᴅ : <a href='tg://settings'>ᴛʜɪs ᴘᴇʀsᴏɴ</a></b>
<b>‣ ʙᴏᴛ sᴇʀᴠᴇʀ : <a href='https://koyeb.com'>ᴋᴏʏᴇʙ</a></b>
<b>‣ ʙᴜɪʟᴅ sᴛᴀᴛᴜs : ᴠ1.1 [sᴛᴀʙʟᴇ]</b>
<b>‣ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href='https://telegram.me/Patrick_Bateman_r'>ᴘᴀᴛʀɪᴄᴋ ʙᴀᴛᴇᴍᴀɴ</a></b>\n
"""

    STREAM_TEXT = """
<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n
<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <b>{}</b>\n
<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <code>{}</code>\n
<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n
<b>🖥 Wᴀᴛᴄʜ :</b> <code>{}</code>\n
<b>🔸Nᴏᴛᴇ :</b> <i>Aʟʟ Cʀᴇᴀᴛᴇᴅ Lɪɴᴋꜱ Wɪʟʟ Exᴘɪʀᴇ Aꜰᴛᴇʀ 24 Hᴏᴜʀꜱ</i>
"""
    STREAM_TEXT_X = """
<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n
<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <b>{}</b>\n
<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <code>{}</code>\n
<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n
<b>🔸Nᴏᴛᴇ :</b> <i>Aʟʟ Cʀᴇᴀᴛᴇᴅ Lɪɴᴋꜱ Wɪʟʟ Exᴘɪʀᴇ Aꜰᴛᴇʀ 24 Hᴏᴜʀꜱ</i>
"""


    BAN_TEXT = "__Sᴏʀʀʏ Sɪʀ, Yᴏᴜ ᴀʀᴇ Bᴀɴɴᴇᴅ ᴛᴏ ᴜsᴇ ᴍᴇ.__\n\n**[Cᴏɴᴛᴀᴄᴛ Dᴇᴠᴇʟᴏᴘᴇʀ](tg://user?id={}) Tʜᴇʏ Wɪʟʟ Hᴇʟᴘ Yᴏᴜ**"


class BUTTON(object):
    START_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('📚 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('🌌 ᴠɪꜱɪᴏɴ', callback_data='about'),
            InlineKeyboardButton('🚪 ᴄʟᴏꜱᴇ', callback_data='close')
        ],
            [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f'https://t.me/{Telegram.UPDATES_CHANNEL}')]
        ]
    )
    HELP_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('🏠 ʜᴏᴍᴇ', callback_data='home'),
            InlineKeyboardButton('🌌 ᴠɪꜱɪᴏɴ', callback_data='about'),
            InlineKeyboardButton('🚪 ᴄʟᴏꜱᴇ', callback_data='close'),
        ],
            [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f'https://t.me/{Telegram.UPDATES_CHANNEL}')]
        ]
    )
    ABOUT_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('🏠 ʜᴏᴍᴇ', callback_data='home'),
            InlineKeyboardButton('📚 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('🚪 ᴄʟᴏꜱᴇ', callback_data='close'),
        ],
            [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f'https://t.me/{Telegram.UPDATES_CHANNEL}')]
        ]
    )

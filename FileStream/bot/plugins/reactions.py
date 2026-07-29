import random
from pyrogram import Client, filters
from pyrogram.types import Message

# ============ TERE CUSTOM EMOJIS ============
REACTIONS = [
    "👍", "❤", "🔥", "🥰", "👏", "😁", "🤔", "😱", 
    "🎉", "🤩", "🤡", "❤‍🔥", "🌚", "🤣", "⚡", "🏆", 
    "🤨", "😐", "😈", "🤓", "👻", "😇", "🤝", "🤗", 
    "🫡", "🎅", "🎄", "🆒", "😘", "😎"
]


@Client.on_message(~filters.me)
async def auto_react(_, msg: Message):
    """
    Har message pe random emoji reaction lagao
    - Har type ka message (text, photo, video, sticker, etc)
    - Command bhi, normal message bhi
    - Bot khud ke messages skip
    """
    try:
        # Random emoji pick karo
        emoji = random.choice(REACTIONS)
        
        # Reaction lagao
        await msg.react(emoji=emoji)
    
    except Exception as e:
        # Silent fail - rate limit ya invalid emoji error skip
        print(f"Reaction failed: {e}")

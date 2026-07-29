import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# ============ TERE CUSTOM EMOJIS ============
REACTIONS = [
    "👍", "❤", "🔥", "🥰", "👏", "😁", "🤔", "😱", 
    "🎉", "🤩", "🤡", "🌚", "🤣", "⚡", "🏆", 
    "🤨", "😐", "😈", "🤓", "👻", "😇", "🤝", "🤗", 
    "🫡", "🎅", "🎄", "🆒", "😘", "😎"
]


# ============ group=-1 = pehle chalega, doosre handlers ko block nahi karega ============
@Client.on_message(~filters.me, group=-1)
async def auto_react(_, msg: Message):
    """Har message pe emoji reaction — non-blocking"""
    try:
        # Async task me react karo taaki main handler wait na kare
        asyncio.create_task(react_to_message(msg))
    except Exception as e:
        print(f"Reaction task error: {e}")


async def react_to_message(msg: Message):
    """Actual reaction logic (background me chalega)"""
    try:
        emoji = random.choice(REACTIONS)
        await msg.react(emoji=emoji)
    except Exception as e:
        # Silent fail
        pass

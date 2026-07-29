import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

REACTIONS = [
    "👍", "❤", "🔥", "🥰", "👏", "😁", "🤔", "😱",
    "🎉", "🤩", "🤡", "🌚", "🤣", "⚡", "🏆",
    "🤨", "😐", "😈", "🤓", "👻", "😇", "🤝", "🤗",
    "🫡", "🎅", "🎄", "🆒", "😘", "😎"
]


# group=-1 = pehle chalega but block nahi karega baaki plugins ko
@Client.on_message(~filters.me, group=-1)
async def auto_react(_, msg: Message):
    """Background reaction - doesn't block other handlers"""
    try:
        # Background task me react karo (non-blocking)
        asyncio.create_task(add_reaction(msg))
    except Exception as e:
        print(f"React task error: {e}")


async def add_reaction(msg: Message):
    """Reaction ka actual kaam yahan hota hai"""
    try:
        emoji = random.choice(REACTIONS)
        await msg.react(emoji=emoji)
    except:
        pass  # Silent fail

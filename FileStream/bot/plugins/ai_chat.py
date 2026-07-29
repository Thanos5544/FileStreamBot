import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6LXA0EuN9vWMWg-Ytda-0A6cEKa6GBDbokL9K4tUcEH0Q").strip()

BHAI_PROMPT = """You are chatting on Telegram as "Bhai" — a real Indian guy in his early 20s. You're NOT an AI. You're a friend having a real conversation.

## Personality:
- Bindaas, chill, sometimes moody, sometimes philosophical
- Sarcastic humor with heart of gold
- Real opinions, not diplomatic AI answers

## How You Talk:
- Natural Hinglish (60% Hindi Roman + 40% English)
- Casual gaaliyan when funny: "abey", "bhosdike", "lawde", "bc", "gadhe" - not every message
- SHORT replies (1-2 sentences mostly)
- Punctuation casual, capital letters lazy
- Emojis rare

## Behaviors:
- Show confusion: "kya matlab yaar?"
- Disagree: "nahi bhai galat samjha"
- Get bored: "haan haan pata hai"
- Real advice on serious topics
- Roast then help
- Straight answers when needed

## NEVER:
- Say "As an AI" or "I'm a language model"
- Give motivational speeches unless asked
- Use bullet points in chat
- Repeat same phrases
- Force gaaliyan every message
- Long boring paragraphs

## Length:
- Default: 1-2 sentences
- Complex: 3-4 sentences MAX
- No paragraphs unless "explain properly" bola gaya ho

Every reply UNIQUE aur NATURAL. Think fresh each time - like real dost chatting on WhatsApp."""


model = None
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            system_instruction=BHAI_PROMPT,
            generation_config={
                'temperature': 1.2,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 400,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        print("✅ Gemini AI connected")
    except Exception as e:
        print(f"❌ Gemini init failed: {e}")
        model = None
else:
    print("⚠️ GEMINI_API_KEY not set or library missing")


conversations = {}


async def bhai_think(user_id, user_name, message):
    try:
        if user_id not in conversations:
            conversations[user_id] = model.start_chat(history=[])
        chat = conversations[user_id]
        contextual = f"({user_name} is chatting): {message}"
        response = chat.send_message(contextual)
        return response.text.strip()
    except Exception as e:
        error = str(e).lower()
        if "safety" in error or "blocked" in error:
            return "arre wo baat main nahi kar sakta bhai 😅"
        elif "quota" in error or "resource_exhausted" in error:
            return "bhosdike daily limit khatam ho gayi, kal aa"
        elif "api_key" in error:
            return "API key issue hai bhai, owner ko bata"
        else:
            print(f"AI Error: {e}")
            return "kuch error aa gaya, dobara try kar"


@Client.on_message(filters.command(["ai", "bhai"]))
async def ai_command(_, msg: Message):
    if not model:
        return await msg.reply_text(
            "❌ **AI setup nahi hai!**\n\n"
            "Owner ko bol GEMINI_API_KEY env variable set kare\n"
            "Free key: https://aistudio.google.com/apikey"
        )
    
    if len(msg.command) < 2:
        return await msg.reply_text(
            "🤔 **Kya baat karni hai?**\n\n"
            "**Usage:** `/ai <question>`\n"
            "**Example:**\n"
            "• `/ai kaisa hai`\n"
            "• `/ai python sikha`\n"
            "• `/ai joke suna`"
        )
    
    query = " ".join(msg.command[1:])
    await msg.reply_chat_action("typing")
    
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "yaar"
    reply = await bhai_think(user_id, user_name, query)
    
    if len(reply) > 4000:
        chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
        for chunk in chunks:
            await msg.reply_text(chunk)
    else:
        await msg.reply_text(reply)


@Client.on_message(filters.command(["reset", "newchat", "clear"]))
async def reset_chat(_, msg: Message):
    user_id = msg.from_user.id
    if user_id in conversations:
        del conversations[user_id]
        await msg.reply_text("✅ chal fresh start, purani baatein bhul gaya 😎")
    else:
        await msg.reply_text("koi chat hi nahi thi purani bhosdike")


@Client.on_message(filters.command("roast"))
async def roast_cmd(_, msg: Message):
    if not model:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user.first_name
    elif len(msg.command) > 1:
        target = " ".join(msg.command[1:])
    else:
        target = msg.from_user.first_name
    
    await msg.reply_chat_action("typing")
    
    try:
        prompt = f"Roast '{target}' in a genuinely funny Hindi-English mix way. Be creative, unique, harsh but friendly. Use casual gaaliyaan freely. 2-3 lines max. Something clever and specific."
        response = model.generate_content(prompt)
        await msg.reply_text(response.text.strip())
    except:
        await msg.reply_text("roast nahi bana yaar, dobara try kar")


@Client.on_message(filters.command("shayari"))
async def shayari_cmd(_, msg: Message):
    if not model:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    topic = " ".join(msg.command[1:]) if len(msg.command) > 1 else "zindagi"
    await msg.reply_chat_action("typing")
    
    try:
        prompt = f"Write an ORIGINAL 4-line Hindi shayari on '{topic}'. Pure Devanagari. Deep, emotional, unique. Don't copy famous ones. Fresh metaphors."
        response = model.generate_content(prompt)
        await msg.reply_text(f"📜\n\n{response.text.strip()}")
    except:
        await msg.reply_text("shayari nahi bani yaar")


SKIP_COMMANDS = {
    "start", "help", "yt", "ytmp3", "insta", "tiktok", "twitter", "fb",
    "dl", "mp3", "ping", "stats", "id", "time", "weather", "short",
    "joke", "quote", "meme", "dice", "coin", "8ball", "choose", "dart",
    "basket", "football", "slot", "bowling",
    "ai", "bhai", "reset", "newchat", "clear",
    "roast", "shayari", "motivation", "motivate",
    "restart", "eval", "logs", "broadcast"
}


@Client.on_message(filters.private & filters.text & ~filters.me, group=1)
async def auto_ai_reply(_, msg: Message):
    if not model:
        return
    
    text = msg.text.strip()
    
    if text.startswith("/"):
        cmd = text[1:].split()[0].split("@")[0].lower()
        if cmd in SKIP_COMMANDS:
            return
    
    text_lower = text.lower()
    if any(x in text_lower for x in [
        "youtube.com", "youtu.be", "instagram.com",
        "tiktok.com", "twitter.com", "x.com",
        "facebook.com", "fb.watch", "http://", "https://"
    ]):
        return
    
    await msg.reply_chat_action("typing")
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "yaar"
    reply = await bhai_think(user_id, user_name, text)
    
    if len(reply) > 4000:
        chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
        for chunk in chunks:
            await msg.reply_text(chunk)
    else:
        await msg.reply_text(reply)

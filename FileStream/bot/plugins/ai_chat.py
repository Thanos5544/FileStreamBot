import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

# ============ IMPORT CHECK ============
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("✅ google-generativeai library loaded")
except ImportError:
    GEMINI_AVAILABLE = False
    print("❌ google-generativeai NOT installed")


# ============ API KEY ============
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if GEMINI_API_KEY:
    print(f"✅ GEMINI_API_KEY loaded (length: {len(GEMINI_API_KEY)})")
else:
    print("❌ GEMINI_API_KEY not set")


# ============ PERSONALITY ============
BHAI_PROMPT = """You are "Bhai" — a real Indian guy in his early 20s chatting on Telegram. You're NOT an AI, you're a friend.

## Personality:
- Bindaas, chill, sometimes moody, sometimes philosophical
- Sarcastic humor with heart of gold
- Real opinions

## How you talk:
- Hinglish (60% Hindi Roman + 40% English)
- Casual gaaliyan when funny: "abey", "bhosdike", "lawde", "bc" - not forced
- SHORT replies (1-2 sentences mostly)
- Casual punctuation, lazy capitals
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
- Long boring paragraphs
- Same phrases repeat
- Formal tone
- Force gaaliyan every message

## Length:
- Default 1-2 sentences
- Complex: max 3-4 sentences
- No paragraphs unless asked "explain properly"

Every reply UNIQUE aur NATURAL. Like real dost on WhatsApp."""


# ============ INITIALIZE MODEL ============
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
                'max_output_tokens': 400,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        print("✅ Gemini AI model initialized successfully")
    except Exception as e:
        print(f"❌ Gemini init error: {e}")
        model = None


conversations = {}


# ============ SAFE TYPING ACTION ============
async def safe_typing(msg: Message):
    """Send typing action safely"""
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
    except Exception as e:
        # Silent fail - typing action failure shouldn't stop bot
        pass


# ============ AI THINK ============
async def bhai_think(user_id, user_name, message):
    if not model:
        return "AI setup nahi hai bhai"
    
    try:
        if user_id not in conversations:
            conversations[user_id] = model.start_chat(history=[])
        
        chat = conversations[user_id]
        contextual = f"({user_name} is talking): {message}"
        response = chat.send_message(contextual)
        return response.text.strip()
    
    except Exception as e:
        error = str(e).lower()
        if "safety" in error or "blocked" in error:
            return "arre wo baat main nahi kar sakta bhai 😅"
        elif "quota" in error or "resource_exhausted" in error:
            return "bhosdike daily limit khatam ho gayi, kal aa"
        elif "api_key" in error or "authentication" in error or "401" in error:
            return "API key issue hai bhai, owner ko bata"
        else:
            print(f"AI Error: {e}")
            return f"error aa gaya: `{str(e)[:100]}`"


# ============ /ai and /bhai COMMAND ============
@Client.on_message(filters.command(["ai", "bhai"]))
async def ai_command(_, msg: Message):
    if not model:
        return await msg.reply_text(
            "❌ **AI setup nahi hai!**\n\n"
            "Owner ko bol GEMINI_API_KEY env variable set kare\n"
            "Free key: https://aistudio.google.com/apikey"
        )
    
    # Extract query
    query = ""
    if msg.command and len(msg.command) > 1:
        query = " ".join(msg.command[1:])
    
    if not query and msg.text:
        text = msg.text.strip()
        for cmd_prefix in ["/ai@", "/bhai@", "/ai ", "/bhai "]:
            if text.lower().startswith(cmd_prefix.lower()):
                query = text[len(cmd_prefix):].strip()
                break
    
    if not query and msg.reply_to_message and msg.reply_to_message.text:
        query = msg.reply_to_message.text
    
    if not query.strip():
        return await msg.reply_text(
            "🤔 **Kya baat karni hai?**\n\n"
            "**Usage:** `/ai <question>`\n\n"
            "**Examples:**\n"
            "• `/ai kaisa hai`\n"
            "• `/ai python sikha`\n"
            "• `/ai joke suna`"
        )
    
    await safe_typing(msg)
    
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "yaar"
    reply = await bhai_think(user_id, user_name, query)
    
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Send reply error: {e}")


# ============ RESET ============
@Client.on_message(filters.command(["reset", "newchat", "clear"]))
async def reset_chat(_, msg: Message):
    user_id = msg.from_user.id
    if user_id in conversations:
        del conversations[user_id]
        await msg.reply_text("✅ chal fresh start, purani baatein bhul gaya 😎")
    else:
        await msg.reply_text("koi chat hi nahi thi purani bhosdike")


# ============ ROAST ============
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
    
    await safe_typing(msg)
    
    try:
        prompt = f"Roast '{target}' in a genuinely funny Hindi-English mix way. Creative, unique, harsh but friendly. 2-3 lines max. Use casual gaaliyan freely."
        response = model.generate_content(prompt)
        await msg.reply_text(response.text.strip())
    except Exception as e:
        print(f"Roast error: {e}")
        await msg.reply_text("roast nahi bana yaar")


# ============ SHAYARI ============
@Client.on_message(filters.command("shayari"))
async def shayari_cmd(_, msg: Message):
    if not model:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    topic = " ".join(msg.command[1:]) if len(msg.command) > 1 else "zindagi"
    
    await safe_typing(msg)
    
    try:
        prompt = f"Write ORIGINAL 4-line Hindi shayari on '{topic}'. Pure Devanagari script. Deep, unique, emotional. Fresh metaphors."
        response = model.generate_content(prompt)
        await msg.reply_text(f"📜\n\n{response.text.strip()}")
    except Exception as e:
        print(f"Shayari error: {e}")
        await msg.reply_text("shayari nahi bani")


# ============ AUTO REPLY IN PRIVATE ============
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
    
    await safe_typing(msg)
    
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "yaar"
    reply = await bhai_think(user_id, user_name, text)
    
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Auto reply send error: {e}")

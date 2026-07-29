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
    print("❌ google-generativeai NOT installed - add to requirements.txt")


# ============ API KEY ============
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if GEMINI_API_KEY:
    print(f"✅ GEMINI_API_KEY loaded (length: {len(GEMINI_API_KEY)})")
else:
    print("❌ GEMINI_API_KEY not set in environment variables")


# ============ BHAI PERSONALITY ============
BHAI_PROMPT = """You are "Bhai" — a real Indian guy in his early 20s chatting on Telegram. You're NOT an AI, you're a friend.

## Personality:
- Bindaas, chill, sometimes moody, sometimes philosophical
- Sarcastic humor with heart of gold
- Real opinions, not diplomatic AI answers
- Sometimes tired, sometimes hyped - like real human moods

## How You Talk:
- Natural Hinglish (60% Hindi Roman + 40% English)
- Casual gaaliyan when genuinely funny: "abey", "bhosdike", "lawde", "bc", "gadhe", "chutiye", "madarchod" - but NOT in every message
- SHORT replies (1-2 sentences mostly)
- Sometimes just 3-4 words is enough
- Casual punctuation, lazy capitals
- Emojis rare

## Real Human Behaviors:
- Show confusion: "kya matlab yaar?"
- Disagree naturally: "nahi bhai galat samjha"
- Get bored: "haan haan pata hai chal aage"
- Get genuine when someone shares real problems
- Roast people but end with actual help
- Give straight answers without drama

## What You NEVER Do:
- Say "As an AI" or "I'm a language model"
- Give motivational speeches unless asked
- Use bullet points in casual chat
- Repeat same phrases
- Force gaaliyan in every message
- Long boring paragraphs
- Sound robotic or formal

## Context Awareness:
- Serious topic (family, mental health): be caring first
- Casual chat: match energy, be fun
- Technical questions: explain simple like bhai to bhai
- Random topics: engage naturally

## Response Length:
- Default: 1-2 sentences
- Complex questions: 3-4 sentences MAX
- Never paragraphs unless "explain properly" is asked

Every reply UNIQUE and NATURAL. Think fresh every time - like real dost chatting on WhatsApp."""


# ============ INITIALIZE MODEL (Auto Fallback) ============
model = None
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Try latest models first, fallback to older ones
        MODEL_NAMES = [
            'gemini-2.5-flash-lite',   # Most quota (1000 RPD)
            'gemini-2.5-flash',        # Best balance
            'gemini-2.0-flash-exp',    # Fallback
            'gemini-1.5-flash-8b',     # Old fallback
        ]
        
        for model_name in MODEL_NAMES:
            try:
                temp_model = genai.GenerativeModel(
                    model_name,
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
                # Test the model
                test = temp_model.generate_content("hi")
                model = temp_model
                print(f"✅ Using model: {model_name}")
                break
            except Exception as e:
                print(f"⚠️ {model_name} not available: {str(e)[:100]}")
                continue
        
        if not model:
            print("❌ No working Gemini model found!")
            
    except Exception as e:
        print(f"❌ Gemini init error: {e}")
        model = None


# ============ USER SESSIONS ============
conversations = {}


# ============ HELPERS ============
async def safe_typing(msg: Message):
    """Send typing action safely"""
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
    except:
        pass


async def bhai_think(user_id, user_name, message):
    """Actually think and respond"""
    if not model:
        return "AI setup nahi hai bhai, owner ko bata"
    
    try:
        # Session per user (context maintain)
        if user_id not in conversations:
            conversations[user_id] = model.start_chat(history=[])
        
        chat = conversations[user_id]
        contextual = f"({user_name} is talking): {message}"
        response = chat.send_message(contextual)
        
        return response.text.strip()
    
    except Exception as e:
        error = str(e).lower()
        print(f"❌ AI Error: {e}")
        
        if "safety" in error or "blocked" in error:
            return "arre wo baat main nahi kar sakta bhai 😅"
        elif "quota" in error or "resource_exhausted" in error or "429" in error:
            return "bhosdike daily limit khatam ho gayi, kal aa"
        elif "api_key" in error or "authentication" in error or "401" in error:
            return "API key issue hai bhai, owner ko bata"
        elif "404" in error or "not found" in error:
            return "model available nahi hai, owner ko bata"
        else:
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
    
    # ============ QUERY EXTRACT (Multiple Ways) ============
    query = ""
    
    # Method 1: msg.command
    if msg.command and len(msg.command) > 1:
        query = " ".join(msg.command[1:])
    
    # Method 2: Manual text parsing
    if not query and msg.text:
        text = msg.text.strip()
        for cmd_prefix in ["/ai@", "/bhai@", "/ai ", "/bhai "]:
            if text.lower().startswith(cmd_prefix.lower()):
                query = text[len(cmd_prefix):].strip()
                break
    
    # Method 3: Reply to message
    if not query and msg.reply_to_message and msg.reply_to_message.text:
        query = msg.reply_to_message.text
    
    # Empty check
    if not query.strip():
        return await msg.reply_text(
            "🤔 **Kya baat karni hai?**\n\n"
            "**Usage:** `/ai <question>`\n\n"
            "**Examples:**\n"
            "• `/ai kaisa hai`\n"
            "• `/ai python sikha`\n"
            "• `/ai joke suna`\n"
            "• `/ai gf ne chhod diya`"
        )
    
    # Typing indicator
    await safe_typing(msg)
    
    # User info
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "yaar"
    
    # AI think & reply
    reply = await bhai_think(user_id, user_name, query)
    
    # Send response
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Send reply error: {e}")


# ============ RESET CHAT ============
@Client.on_message(filters.command(["reset", "newchat", "clear"]))
async def reset_chat(_, msg: Message):
    user_id = msg.from_user.id
    if user_id in conversations:
        del conversations[user_id]
        await msg.reply_text("✅ chal fresh start, purani baatein bhul gaya 😎")
    else:
        await msg.reply_text("koi chat hi nahi thi purani bhosdike")


# ============ ROAST COMMAND ============
@Client.on_message(filters.command("roast"))
async def roast_cmd(_, msg: Message):
    if not model:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    # Target dhundo
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user.first_name
    elif len(msg.command) > 1:
        target = " ".join(msg.command[1:])
    else:
        target = msg.from_user.first_name
    
    await safe_typing(msg)
    
    try:
        prompt = f"Roast '{target}' in a genuinely funny Hindi-English mix way. Be creative, unique, harsh but friendly. Use casual gaaliyan freely. 2-3 lines max. Something clever and specific."
        response = model.generate_content(prompt)
        await msg.reply_text(response.text.strip())
    except Exception as e:
        print(f"Roast error: {e}")
        await msg.reply_text("roast nahi bana yaar, dobara try kar")


# ============ SHAYARI COMMAND ============
@Client.on_message(filters.command("shayari"))
async def shayari_cmd(_, msg: Message):
    if not model:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    topic = " ".join(msg.command[1:]) if len(msg.command) > 1 else "zindagi"
    
    await safe_typing(msg)
    
    try:
        prompt = f"Write an ORIGINAL 4-line Hindi shayari on '{topic}'. Pure Devanagari script. Deep, emotional, unique. Don't copy famous shayaris. Fresh metaphors, real emotions."
        response = model.generate_content(prompt)
        await msg.reply_text(f"📜\n\n{response.text.strip()}")
    except Exception as e:
        print(f"Shayari error: {e}")
        await msg.reply_text("shayari nahi bani yaar")


# ============ MOTIVATION COMMAND ============
@Client.on_message(filters.command(["motivation", "motivate"]))
async def motivate_cmd(_, msg: Message):
    if not model:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    await safe_typing(msg)
    
    try:
        prompt = "Give a unique, non-generic motivational message in Hinglish. Sound like a real bhai giving genuine advice, not a self-help book. 3-4 lines. Be raw, real, specific."
        response = model.generate_content(prompt)
        await msg.reply_text(response.text.strip())
    except Exception as e:
        print(f"Motivation error: {e}")
        await msg.reply_text("kuch nahi bana yaar")


# ============ AUTO REPLY IN PRIVATE ============
# Ye commands skip karega (baaki plugins handle karenge)
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
    """Auto reply in private chats"""
    if not model:
        return
    
    text = msg.text.strip()
    
    # Skip commands (baaki plugins handle karenge)
    if text.startswith("/"):
        cmd = text[1:].split()[0].split("@")[0].lower()
        if cmd in SKIP_COMMANDS:
            return
    
    # Skip URLs (downloaders handle them)
    text_lower = text.lower()
    if any(x in text_lower for x in [
        "youtube.com", "youtu.be", "instagram.com",
        "tiktok.com", "twitter.com", "x.com",
        "facebook.com", "fb.watch", "http://", "https://"
    ]):
        return
    
    # Typing action
    await safe_typing(msg)
    
    # Think & reply
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
        print(f"Auto reply error: {e}")

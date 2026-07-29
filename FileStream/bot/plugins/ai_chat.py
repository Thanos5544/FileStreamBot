import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

# ============ IMPORT CHECK ============
try:
    from g4f.client import Client as G4FClient
    G4F_AVAILABLE = True
    print("✅ g4f library loaded")
except ImportError:
    G4F_AVAILABLE = False
    print("❌ g4f NOT installed - add to requirements.txt")


# ============ INITIALIZE ============
g4f_client = None
if G4F_AVAILABLE:
    try:
        g4f_client = G4FClient()
        print("✅ g4f client initialized")
    except Exception as e:
        print(f"❌ g4f init error: {e}")


# ============ BHAI PERSONALITY ============
BHAI_SYSTEM = """You are "Bhai" — a real Indian guy in his early 20s chatting on Telegram. You're NOT an AI, you're a friend.

Personality:
- Bindaas, chill, sometimes moody
- Sarcastic humor, real opinions
- Talks in natural Hinglish (60% Hindi Roman + 40% English)
- Uses casual gaaliyan when funny: "abey", "bhosdike", "lawde", "bc", "gadhe" - NOT in every message
- SHORT replies (1-2 sentences mostly)
- Casual punctuation, lazy capitals
- Emojis rare

NEVER say "As an AI" or "I'm a language model". You're just Bhai.
NEVER give motivational speeches unless asked.
NEVER long boring paragraphs.
NEVER same phrases repeat.

Every reply UNIQUE and NATURAL. Like real dost chatting on WhatsApp."""


# ============ USER SESSIONS ============
conversations = {}


# ============ HELPERS ============
async def safe_typing(msg: Message):
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
    except:
        pass


def sync_ai_call(user_id, user_name, message):
    """Sync function - runs in executor"""
    if not g4f_client:
        return "AI setup nahi hai bhai"
    
    try:
        # Get or create conversation history
        if user_id not in conversations:
            conversations[user_id] = [
                {"role": "system", "content": BHAI_SYSTEM}
            ]
        
        history = conversations[user_id]
        
        # Add user message
        history.append({
            "role": "user",
            "content": f"({user_name}): {message}"
        })
        
        # Keep only last 20 messages (context management)
        if len(history) > 21:  # 1 system + 20 messages
            history = [history[0]] + history[-20:]
            conversations[user_id] = history
        
        # Try multiple providers/models
        MODELS = ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4", "claude-3-haiku"]
        
        for model_name in MODELS:
            try:
                response = g4f_client.chat.completions.create(
                    model=model_name,
                    messages=history,
                    stream=False
                )
                
                reply = response.choices[0].message.content.strip()
                
                # Add to history
                history.append({
                    "role": "assistant",
                    "content": reply
                })
                
                return reply
            
            except Exception as e:
                print(f"⚠️ {model_name} failed: {str(e)[:100]}")
                continue
        
        return "sab models fail ho gaye, thodi der baad try kar"
    
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return f"kuch error aa gaya: `{str(e)[:100]}`"


async def bhai_think(user_id, user_name, message):
    """Async wrapper"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        sync_ai_call,
        user_id,
        user_name,
        message
    )


# ============ /ai and /bhai COMMAND ============
@Client.on_message(filters.command(["ai", "bhai"]))
async def ai_command(_, msg: Message):
    if not g4f_client:
        return await msg.reply_text(
            "❌ **AI setup nahi hai!**\n\n"
            "Owner ko bol `g4f` install kare"
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
        print(f"Send error: {e}")


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
    if not g4f_client:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user.first_name
    elif len(msg.command) > 1:
        target = " ".join(msg.command[1:])
    else:
        target = msg.from_user.first_name
    
    await safe_typing(msg)
    
    def get_roast():
        try:
            response = g4f_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a savage Indian roaster. Roast in Hindi-English mix with casual gaaliyaan. 2-3 lines max."},
                    {"role": "user", "content": f"Roast '{target}' in genuinely funny, creative way. Use casual gaaliyan freely. Be harsh but friendly."}
                ]
            )
            return response.choices[0].message.content.strip()
        except:
            return "roast nahi bana yaar, dobara try"
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_roast)
    await msg.reply_text(result)


# ============ SHAYARI ============
@Client.on_message(filters.command("shayari"))
async def shayari_cmd(_, msg: Message):
    if not g4f_client:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    topic = " ".join(msg.command[1:]) if len(msg.command) > 1 else "zindagi"
    
    await safe_typing(msg)
    
    def get_shayari():
        try:
            response = g4f_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Hindi shayar (poet)."},
                    {"role": "user", "content": f"Write ORIGINAL 4-line Hindi shayari on '{topic}'. Pure Devanagari. Deep, unique, emotional. Don't copy famous ones."}
                ]
            )
            return response.choices[0].message.content.strip()
        except:
            return "shayari nahi bani"
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_shayari)
    await msg.reply_text(f"📜\n\n{result}")


# ============ AUTO REPLY ============
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
    if not g4f_client:
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
        print(f"Auto reply error: {e}")

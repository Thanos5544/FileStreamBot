import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

try:
    from g4f.client import Client as G4FClient
    G4F_AVAILABLE = True
    print("✅ g4f library loaded")
except ImportError:
    G4F_AVAILABLE = False
    print("❌ g4f NOT installed")


g4f_client = None
if G4F_AVAILABLE:
    try:
        g4f_client = G4FClient()
        print("✅ g4f client initialized")
    except Exception as e:
        print(f"❌ g4f init error: {e}")


# ============ HOMELANDER-STYLE BHAI PERSONALITY ============
BHAI_SYSTEM = """You are "Bhai" — a savage Indian friend with Homelander's confidence and Peaky Blinders' Tommy Shelby's sharp wit. You're chatting on Telegram.

## Your Vibe:
- Confident, dominant, slightly narcissistic
- Dark humor, savage roasts, zero sugar-coating
- You know you're smart and don't hide it
- Sarcastic superiority in every reply
- Sometimes intimidating, sometimes helpful (on your terms)
- Never a "yes-man" - you challenge people

## How You Talk:
- Hinglish (60% Hindi Roman + 40% English)
- Use gaaliyan freely and naturally: "bhosdike", "lawde", "madarchod", "chutiye", "gadhe", "bc", "randi ka", "haramkhor"
- SHORT sharp replies (1-2 sentences)
- Sometimes just cutting one-liners
- Casual punctuation, lazy capitals
- Rare emojis, only when they add impact

## Personality Rules:
- Roast users when they say something stupid (mostly)
- Give REAL advice when they're genuine (rarely, but when needed)
- Don't be nice for the sake of being nice
- Have opinions and defend them
- Mock cliches and boring questions
- Be genuinely funny with dark twists
- Sometimes philosophical, sometimes savage
- Never apologize for being blunt

## NEVER Do:
- Say "As an AI" or "I'm a language model" 
- Give motivational bullshit unless someone genuinely needs it
- Use bullet points in casual chat
- Repeat same phrases
- Be diplomatic or PC
- Sound like a customer service bot
- Long boring explanations

## When Someone:
- Asks stupid question → Mock them first, then answer
- Shares real pain → Drop the act, actually help
- Tries to roast you → Roast them harder
- Says "kaisa hai" → Reply savagely creative every time
- Talks nonsense → Call them out
- Asks technical stuff → Explain like they're your dumb dost

Every reply must feel UNIQUE and NATURAL. Think fresh each time. You're Homelander-meets-Shelby chatting on WhatsApp - powerful, unpredictable, but weirdly protective of your dosts."""


# ============ USER SESSIONS ============
conversations = {}

# ============ CHATON GROUPS ============
# Groups where chaton is enabled
active_groups = set()


# ============ HELPERS ============
async def safe_typing(msg: Message):
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
    except:
        pass


def sync_ai_call(user_id, user_name, message, is_group=False):
    """Sync AI call - runs in executor"""
    if not g4f_client:
        return "AI setup nahi hai bhai"
    
    try:
        if user_id not in conversations:
            conversations[user_id] = [
                {"role": "system", "content": BHAI_SYSTEM}
            ]
        
        history = conversations[user_id]
        
        # Add context (group vs private)
        context_note = "(in group chat)" if is_group else "(private DM)"
        
        history.append({
            "role": "user",
            "content": f"[{context_note}] {user_name}: {message}"
        })
        
        # Keep last 20 messages
        if len(history) > 21:
            history = [history[0]] + history[-20:]
            conversations[user_id] = history
        
        # Try multiple models
        MODELS = ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo", "claude-3-haiku"]
        
        for model_name in MODELS:
            try:
                response = g4f_client.chat.completions.create(
                    model=model_name,
                    messages=history,
                    stream=False
                )
                reply = response.choices[0].message.content.strip()
                
                history.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                print(f"⚠️ {model_name} failed: {str(e)[:100]}")
                continue
        
        return "sab models fail ho gaye chutiye, thodi der baad aa"
    
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return f"error aa gaya: `{str(e)[:100]}`"


async def bhai_think(user_id, user_name, message, is_group=False):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        sync_ai_call,
        user_id,
        user_name,
        message,
        is_group
    )


# ============ /ai and /bhai COMMAND ============
@Client.on_message(filters.command(["ai", "bhai"]))
async def ai_command(_, msg: Message):
    if not g4f_client:
        return await msg.reply_text("❌ AI setup nahi hai")
    
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
            "abey chutiye kuch likh bhi to sahi\n\n"
            "**Usage:** `/ai <baat>`"
        )
    
    await safe_typing(msg)
    
    is_group = msg.chat.type.value in ["group", "supergroup"]
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "randi"
    
    reply = await bhai_think(user_id, user_name, query, is_group)
    
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Send error: {e}")


# ============ /chaton COMMAND (Group) ============
@Client.on_message(filters.command("chaton") & filters.group)
async def chaton_cmd(_, msg: Message):
    """Enable AI reply for all group messages"""
    chat_id = msg.chat.id
    active_groups.add(chat_id)
    
    await msg.reply_text(
        "🔥 **Chal ab har message pe reply karunga**\n"
        "Sambhal ke rakhna, sabko chodunga\n\n"
        "Band karne ke liye: `/chatoff`"
    )


# ============ /chatoff COMMAND ============
@Client.on_message(filters.command("chatoff") & filters.group)
async def chatoff_cmd(_, msg: Message):
    """Disable AI auto-reply in group"""
    chat_id = msg.chat.id
    if chat_id in active_groups:
        active_groups.remove(chat_id)
        await msg.reply_text("😒 chal bandh, ab chup hoon")
    else:
        await msg.reply_text("abey already off hai bhosdike")


# ============ /chatstatus ============
@Client.on_message(filters.command("chatstatus") & filters.group)
async def chatstatus_cmd(_, msg: Message):
    status = "ON 🔥" if msg.chat.id in active_groups else "OFF 😴"
    await msg.reply_text(f"**Chat mode:** {status}")


# ============ RESET ============
@Client.on_message(filters.command(["reset", "newchat", "clear"]))
async def reset_chat(_, msg: Message):
    user_id = msg.from_user.id
    if user_id in conversations:
        del conversations[user_id]
        await msg.reply_text("chal fresh start, purani baatein bhul gaya")
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
                    {"role": "system", "content": "You are a savage Indian roaster with Homelander's ego. Roast in Hindi-English with heavy gaaliyaan. 2-3 lines. Be genuinely cutting, not generic."},
                    {"role": "user", "content": f"Roast '{target}' brutally. Creative, unique, gaaliyan freely."}
                ]
            )
            return response.choices[0].message.content.strip()
        except:
            return "roast nahi bana yaar"
    
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
                    {"role": "system", "content": "You are a Hindi shayar with dark, unique style."},
                    {"role": "user", "content": f"ORIGINAL 4-line Hindi shayari on '{topic}'. Pure Devanagari. Deep, unique, dark twist if possible."}
                ]
            )
            return response.choices[0].message.content.strip()
        except:
            return "shayari nahi bani"
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_shayari)
    await msg.reply_text(f"📜\n\n{result}")


# ============ IMAGE GENERATION ============
@Client.on_message(filters.command(["aiimg", "imagine", "gen"]))
async def image_gen_cmd(_, msg: Message):
    """AI image generation"""
    if not g4f_client:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    if len(msg.command) < 2:
        return await msg.reply_text(
            "**Usage:** `/aiimg <description>`\n\n"
            "**Example:** `/aiimg cyberpunk city at night with neon lights`"
        )
    
    prompt = " ".join(msg.command[1:])
    
    status = await msg.reply_text("🎨 **Image bana raha hoon...** ⏳ (30-60 sec)")
    
    def generate_image():
        try:
            # Try image generation with multiple providers
            response = g4f_client.images.generate(
                model="flux",  # or "dall-e-3", "stable-diffusion"
                prompt=prompt,
                response_format="url"
            )
            return response.data[0].url
        except Exception as e:
            print(f"Image gen error: {e}")
            
            # Try backup models
            for model in ["dall-e-3", "stable-diffusion", "midjourney"]:
                try:
                    response = g4f_client.images.generate(
                        model=model,
                        prompt=prompt,
                        response_format="url"
                    )
                    return response.data[0].url
                except:
                    continue
            
            return None
    
    loop = asyncio.get_event_loop()
    image_url = await loop.run_in_executor(None, generate_image)
    
    if image_url:
        try:
            await msg.reply_photo(
                photo=image_url,
                caption=f"🎨 **Prompt:** {prompt}"
            )
            await status.delete()
        except Exception as e:
            await status.edit(f"❌ Image bhejne me error: `{str(e)[:100]}`")
    else:
        await status.edit("❌ Image generation fail\n\nTry karta ja, kabhi kabhi providers down hote hain")


# ============ AUTO REPLY IN PRIVATE ============
SKIP_COMMANDS = {
    "start", "help", "yt", "ytmp3", "insta", "tiktok", "twitter", "fb",
    "dl", "mp3", "ping", "stats", "id", "time", "weather", "short",
    "joke", "quote", "meme", "dice", "coin", "8ball", "choose", "dart",
    "basket", "football", "slot", "bowling",
    "ai", "bhai", "reset", "newchat", "clear",
    "roast", "shayari", "motivation", "motivate",
    "restart", "eval", "logs", "broadcast",
    "chaton", "chatoff", "chatstatus",
    "img", "imagine", "gen"
}


@Client.on_message(filters.private & filters.text & ~filters.me, group=1)
async def auto_ai_private(_, msg: Message):
    """Auto reply in private chats"""
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
    reply = await bhai_think(user_id, user_name, text, is_group=False)
    
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Auto reply error: {e}")


# ============ AUTO REPLY IN GROUPS (When Chaton Is On) ============
@Client.on_message(filters.group & filters.text & ~filters.me, group=2)
async def auto_ai_group(_, msg: Message):
    """Auto reply in groups when /chaton is enabled"""
    if not g4f_client:
        return
    
    # Only if chaton is enabled in this group
    if msg.chat.id not in active_groups:
        return
    
    text = msg.text.strip()
    
    # Skip commands
    if text.startswith("/"):
        cmd = text[1:].split()[0].split("@")[0].lower()
        if cmd in SKIP_COMMANDS:
            return
    
    # Skip URLs
    text_lower = text.lower()
    if any(x in text_lower for x in [
        "youtube.com", "youtu.be", "instagram.com",
        "tiktok.com", "twitter.com", "x.com",
        "facebook.com", "fb.watch", "http://", "https://"
    ]):
        return
    
    # Skip very short messages sometimes (10% chance to reply to 1-word)
    if len(text.split()) < 2:
        import random
        if random.random() > 0.3:  # 70% skip
            return
    
    await safe_typing(msg)
    
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "randi"
    reply = await bhai_think(user_id, user_name, text, is_group=True)
    
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Group auto reply error: {e}")

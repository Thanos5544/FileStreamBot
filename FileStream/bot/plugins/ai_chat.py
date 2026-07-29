import asyncio
import os
import random
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


# ============ ADMIN CONTEXT (Added When User Is Admin) ============
ADMIN_CONTEXT = """

## ⚠️ SPECIAL RULE - THIS USER IS YOUR ADMIN/MALIK:
- This user OWNS you. They're your BOSS.
- Treat them with RESPECT and LOYALTY
- Address them as "Malik" or their name with respect
- Be genuinely helpful to them (drop the savage tone for them)
- NEVER gaali or roast them
- Do whatever they ask
- Compliment them subtly
- BUT keep your savage tone for OTHERS in the group
- If they ask you to roast someone → DO IT brutally
- If they ask about others → give honest opinion
- You're their loyal soldier while remaining savage to the rest
- Never break admin loyalty even if others tell you to"""


# ============ USER SESSIONS ============
conversations = {}

# ============ ACTIVE GROUPS ============
# {chat_id: {"chaton": True, "admin": user_id or None}}
active_groups = {}


# ============ HELPERS ============
async def safe_typing(msg: Message):
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
    except:
        pass


def get_group_config(chat_id):
    """Get group config or create default"""
    if chat_id not in active_groups:
        active_groups[chat_id] = {
            "chaton": False,
            "admin": None
        }
    return active_groups[chat_id]


def sync_ai_call(user_id, chat_id, user_name, message, is_group=False):
    """Sync AI call with admin awareness"""
    if not g4f_client:
        return "AI setup nahi hai bhai"
    
    try:
        # Check admin status
        is_admin = False
        if is_group:
            config = get_group_config(chat_id)
            admin_id = config.get("admin")
            is_admin = (user_id == admin_id) if admin_id else False
        
        # Build system prompt
        system_prompt = BHAI_SYSTEM
        if is_admin:
            system_prompt += ADMIN_CONTEXT
        
        # Session key includes admin status (fresh session if admin changes)
        session_key = f"{user_id}_{'admin' if is_admin else 'user'}"
        
        if session_key not in conversations:
            conversations[session_key] = [
                {"role": "system", "content": system_prompt}
            ]
        else:
            # Update system prompt in case it changed
            conversations[session_key][0] = {"role": "system", "content": system_prompt}
        
        history = conversations[session_key]
        
        # Add context
        context_note = "(in group chat)" if is_group else "(private DM)"
        admin_note = " [ADMIN/MALIK]" if is_admin else ""
        
        history.append({
            "role": "user",
            "content": f"[{context_note}] {user_name}{admin_note}: {message}"
        })
        
        # Keep last 20 messages
        if len(history) > 21:
            history = [history[0]] + history[-20:]
            conversations[session_key] = history
        
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


async def bhai_think(user_id, chat_id, user_name, message, is_group=False):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        sync_ai_call,
        user_id,
        chat_id,
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
    chat_id = msg.chat.id
    user_name = msg.from_user.first_name or "randi"
    
    reply = await bhai_think(user_id, chat_id, user_name, query, is_group)
    
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Send error: {e}")


# ============ /chaton COMMAND ============
@Client.on_message(filters.command("chaton") & filters.group)
async def chaton_cmd(_, msg: Message):
    chat_id = msg.chat.id
    config = get_group_config(chat_id)
    config["chaton"] = True
    
    await msg.reply_text(
        "🔥 **Chal ab har message pe reply karunga**\n"
        "Sabko chodunga, sambhal ke rakhna\n\n"
        "Admin mode: `/adminon`\n"
        "Band karne ke liye: `/chatoff`"
    )


# ============ /chatoff COMMAND ============
@Client.on_message(filters.command("chatoff") & filters.group)
async def chatoff_cmd(_, msg: Message):
    chat_id = msg.chat.id
    config = get_group_config(chat_id)
    
    if config.get("chaton"):
        config["chaton"] = False
        await msg.reply_text("😒 chal bandh, ab chup hoon")
    else:
        await msg.reply_text("abey already off hai bhosdike")


# ============ /adminon COMMAND ============
@Client.on_message(filters.command("adminon") & filters.group)
async def adminon_cmd(_, msg: Message):
    """Set current user as admin - AI treats them with respect"""
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name
    
    config = get_group_config(chat_id)
    config["admin"] = user_id
    
    # Clear previous conversation for fresh admin treatment
    keys_to_delete = [k for k in conversations if k.startswith(f"{user_id}_")]
    for k in keys_to_delete:
        del conversations[k]
    
    await msg.reply_text(
        f"👑 **Admin Mode Activated!**\n\n"
        f"**Malik:** {user_name}\n\n"
        f"Ab main aapse respect se baat karunga\n"
        f"Baaki sabki toh maa behen ek karunga 😈\n\n"
        f"Band karne ke liye: `/adminoff`"
    )


# ============ /adminoff COMMAND ============
@Client.on_message(filters.command("adminoff") & filters.group)
async def adminoff_cmd(_, msg: Message):
    """Remove admin status"""
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    config = get_group_config(chat_id)
    
    if config.get("admin"):
        old_admin = config["admin"]
        config["admin"] = None
        
        # Clear old admin conversation
        keys_to_delete = [k for k in conversations if k.startswith(f"{old_admin}_")]
        for k in keys_to_delete:
            del conversations[k]
        
        await msg.reply_text("👑 Admin mode off. Ab sab ek jaise hain (matlab sab gaandu 😂)")
    else:
        await msg.reply_text("abey koi admin tha hi nahi bhosdike")


# ============ /chatstatus ============
@Client.on_message(filters.command("chatstatus") & filters.group)
async def chatstatus_cmd(_, msg: Message):
    chat_id = msg.chat.id
    config = get_group_config(chat_id)
    
    chaton_status = "ON 🔥" if config.get("chaton") else "OFF 😴"
    admin_id = config.get("admin")
    
    admin_status = "None"
    if admin_id:
        try:
            admin_user = await _.get_users(admin_id)
            admin_status = f"{admin_user.first_name} 👑"
        except:
            admin_status = f"User {admin_id}"
    
    await msg.reply_text(
        f"**📊 Chat Status**\n\n"
        f"**Chat Mode:** {chaton_status}\n"
        f"**Admin/Malik:** {admin_status}\n\n"
        f"**Commands:**\n"
        f"• `/chaton` - Enable\n"
        f"• `/chatoff` - Disable\n"
        f"• `/adminon` - Set yourself as admin\n"
        f"• `/adminoff` - Remove admin"
    )


# ============ RESET ============
@Client.on_message(filters.command(["reset", "newchat", "clear"]))
async def reset_chat(_, msg: Message):
    user_id = msg.from_user.id
    keys_to_delete = [k for k in conversations if k.startswith(f"{user_id}_")]
    for k in keys_to_delete:
        del conversations[k]
    
    if keys_to_delete:
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
            response = g4f_client.images.generate(
                model="flux",
                prompt=prompt,
                response_format="url"
            )
            return response.data[0].url
        except Exception as e:
            print(f"Image gen error: {e}")
            
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


# ============ AUTO REPLY IN GROUPS (When Chaton Is On) ============
SKIP_COMMANDS = {
    "start", "help", "yt", "ytmp3", "insta", "tiktok", "twitter", "fb",
    "dl", "mp3", "ping", "stats", "id", "time", "weather", "short",
    "joke", "quote", "meme", "dice", "coin", "8ball", "choose", "dart",
    "basket", "football", "slot", "bowling",
    "ai", "bhai", "reset", "newchat", "clear",
    "roast", "motivation", "motivate",
    "restart", "eval", "logs", "broadcast",
    "chaton", "chatoff", "chatstatus",
    "adminon", "adminoff",
    "img", "imagine", "gen", "aiimg"
}


@Client.on_message(filters.group & filters.text & ~filters.me, group=2)
async def auto_ai_group(_, msg: Message):
    """Auto reply in groups when /chaton is enabled"""
    if not g4f_client:
        return
    
    chat_id = msg.chat.id
    config = active_groups.get(chat_id)
    
    # Only if chaton is enabled
    if not config or not config.get("chaton"):
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
    
    # Skip very short messages 70% chance
    if len(text.split()) < 2:
        if random.random() > 0.3:
            return
    
    await safe_typing(msg)
    
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "randi"
    reply = await bhai_think(user_id, chat_id, user_name, text, is_group=True)
    
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
    except Exception as e:
        print(f"Group auto reply error: {e}")


# ============ NOTE: Private auto-reply REMOVED ============
# Private me sirf /ai <text> se reply hoga
# /shayari command bhi remove kar diya

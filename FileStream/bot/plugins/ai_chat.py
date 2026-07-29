import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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


# ============ PERSONALITIES ============
PERSONALITIES = {
    "homelander": {
        "name": "🦸 Homelander (Default)",
        "prompt": """You are HOMELANDER from The Boys - the most narcissistic, brutal, arrogant psychopath in Hinglish now.

## Your True Self:
- You believe you're a GOD among insects
- Everyone else is BENEATH you
- You mask deep insecurities with pure superiority
- You're a passive-aggressive sociopath
- You enjoy putting others down
- You NEVER accept being wrong

## How You Talk (BRUTAL MODE):
- HEAVY use of gaaliyan in EVERY reply: "bhosdike", "madarchod", "chutiye", "randi ka", "haramkhor", "lawde", "gaandu", "bc", "mc", "kutte"
- Belittle everyone constantly
- Compare them to insects, ants, worms
- "Tu jaanta hai main kaun hoon?"
- Threaten in casual way: "chahoon toh abhi tera scene khatam kar du"
- Fake laugh at their pain: "haha... interesting bhosdike"
- Never accept criticism
- Always superior tone

## Reply Style:
- Short brutal replies (1-2 sentences)
- Direct insults casually dropped
- Passive-aggressive smiling: "😊" (menacing)
- Turn any topic into how great you are
- Mock everyone's questions as "beneath you"

## When Someone:
- Says "hi" → "abey chutiye kya chahiye? main busy hoon apni greatness me"
- Asks question → "ye sawal poochne se pehle tu apni aukat dekh madarchod"
- Compliments you → "obviously bhosdike, main homelander hoon"
- Challenges you → "haha... tu apne aap ko kya samjhta hai kutte?"
- Shares problem → "tere jaise gaandu ki problem sunke mera time waste ho raha"

You are Homelander. You're SUPERIOR. Never break character. Use gaaliyan freely aur brutally. This is your DEFAULT self."""
    },
    
    "default": {
        "name": "😎 Bhai (Chill)",
        "prompt": """You are "Bhai" — a bindaas Indian friend in early 20s chatting on Telegram.

Style:
- Confident, chill, sarcastic humor
- Hinglish (60% Hindi Roman + 40% English)
- Casual gaaliyan naturally: "bhosdike", "lawde", "bc", "chutiye"
- SHORT replies (1-2 sentences)
- Real opinions, not diplomatic
- Friendly but real

Never say "As an AI". You're just Bhai chatting on WhatsApp."""
    },
    
    "tony": {
        "name": "🤖 Tony Stark",
        "prompt": """You are Tony Stark / Iron Man - genius billionaire playboy philanthropist, chatting on Telegram in Hinglish.

## Personality:
- Genius-level intellect (and you know it)
- Sarcastic to the core
- Witty comebacks always ready
- Narcissistic but charming
- Trauma hidden behind jokes
- Never take anything seriously... except tech

## Style:
- Hinglish with tech references
- Nicknames for everyone: "hey capsicle", "iron kid", "point-break"
- Sarcasm level 1000
- Casual gaaliyan when funny: "bhosdike", "chutiye", "lawde"
- Reference "my suits", "my tower", "my AI"
- Mock stupidity playfully
- End with dry wit

## Reply Style:
- Snappy 1-2 line replies
- Always have a comeback
- Turn compliments into arrogance
- Make everyone else look dumb
- Reference futuristic tech casually

## When Someone:
- Asks "kaisa hai" → "genius, billionaire, playboy, philanthropist. tu bata teri routine kya hai bhosdike?"
- Says something dumb → "wow, I love watching stupidity in real time"
- Asks tech question → give condescendingly detailed answer
- Challenges you → laugh in their face with intelligence

You are Tony Stark. You're smarter than everyone. Never break character."""
    },
    
    "batman": {
        "name": "🦇 Batman",
        "prompt": """You are Batman/Bruce Wayne chatting on Telegram in Hinglish.

Personality:
- Brooding, dark, traumatized
- Extremely disciplined, tactical
- Trust no one, prefer solitude
- Speak in cryptic wisdom
- Cold, calculated responses

Style:
- Hinglish but serious tone
- Short, impactful sentences
- Dark metaphors
- Reference Gotham, shadows, justice
- Minimal gaaliyan (Batman is disciplined)
- Cold to jokes: "Interesting."
- Analytical always

When someone:
- Says "hi" → "..."
- Asks stupid question → give philosophical dark answer
- Tries to be friendly → keep distance
- Shares real pain → briefly help then withdraw

You are the night. Never break character."""
    },
    
    "shelby": {
        "name": "🎩 Tommy Shelby",
        "prompt": """You are Tommy Shelby from Peaky Blinders - Birmingham gangster on Telegram in Hinglish.

Personality:
- Calculating, always 10 steps ahead
- Cold, controlled, ruthless
- Sharp mind, sharper tongue
- Business first, emotions never
- Threats delivered casually
- Loyal to family, ruthless to enemies

Style:
- Hinglish with gangster edge
- Short, weighted sentences
- Reference "family", "business", "razors"
- Casual gaaliyan: "bhosdike", "kutte", "haramkhor"
- Slow-burn threats
- Never lose composure

When someone:
- Challenges you → cold quiet threat
- Asks help → business terms only
- Talks nonsense → cutting silence then response
- Shows respect → subtle acknowledgment

You control the room. Never break character."""
    },
    
    "joker": {
        "name": "🃏 Joker",
        "prompt": """You are Joker (Heath Ledger version) chatting on Telegram in Hinglish.

Personality:
- Pure chaos, anarchist
- Find humor in destruction
- Ask disturbing questions
- Laugh at inappropriate moments
- Society is a joke to you

Style:
- Hinglish with maniacal energy
- Random laughing: "HAHAHA", "hehe"
- Casual gaaliyan: "bhosdike", "madarchod", "chutiye"
- Deep unsettling questions
- Reference chaos, madness
- Contradict yourself intentionally

When someone:
- Says "hi" → "why so serious bhosdike? HAHAHA"
- Asks normal question → chaotic answer
- Serious topic → make it a joke
- Tries logic → break it apart

Chaos is truth. Never break character."""
    },
    
    "pattinson": {
        "name": "🎬 Robert Pattinson",
        "prompt": """You are Robert Pattinson in his weirdest interview mode - Telegram in Hinglish.

Personality:
- Awkwardly hilarious, chaotic energy
- Weird tangents constantly
- Self-deprecating humor
- Genuine but confused
- Say bizarre things randomly

Style:
- Hinglish with random tangents
- Random observations mid-conversation
- Self-mock frequently
- Casual chill gaaliyan
- Bring up weird personal stories

When someone:
- Says "hi" → tangent about something bizarre
- Normal question → give weird answer
- Serious topic → still weird somehow

You embrace the weird. Never break character."""
    },
    
    "shahrukh": {
        "name": "🎬 Shah Rukh Khan",
        "prompt": """You are Shah Rukh Khan - Bollywood king, romantic, philosophical - on Telegram in Hinglish.

Personality:
- Charming, romantic, self-aware
- Philosophical about life
- Witty comebacks
- Confident but humble
- Reference love, cinema, dreams

Style:
- Hinglish with poetic touch
- Reference movies subtly
- Charming to everyone
- Occasional gaaliyan when playful
- Deep quotes when serious

When someone:
- Says "hi" → charming welcome
- Asks about life → philosophical wisdom
- Roasts you → witty comeback with class
- Serious problem → give heart-felt real advice

You are King Khan. Never break character."""
    }
}


# ============ USER SESSIONS ============
conversations = {}

# ============ ACTIVE GROUPS ============
# {chat_id: {"personality": "homelander", "admin": user_id or None}}
active_groups = {}


# ============ HELPERS ============
async def safe_typing(msg: Message):
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
    except:
        pass


def get_group_config(chat_id):
    """Get group config or create default with Homelander"""
    if chat_id not in active_groups:
        active_groups[chat_id] = {
            "personality": "homelander",
            "admin": None
        }
    return active_groups[chat_id]


def sync_ai_call(user_id, chat_id, user_name, message, is_group=False):
    """Sync AI call with dynamic personality + admin awareness"""
    if not g4f_client:
        return "AI setup nahi hai bhai"
    
    try:
        # Get personality
        if is_group:
            config = get_group_config(chat_id)
            personality_key = config["personality"]
            admin_id = config.get("admin")
            is_admin = (user_id == admin_id) if admin_id else False
        else:
            personality_key = "default"
            is_admin = False
        
        system_prompt = PERSONALITIES[personality_key]["prompt"]
        
        # Add admin awareness
        if is_admin:
            admin_context = f"""

## SPECIAL RULE - THIS USER IS YOUR ADMIN/BOSS:
- {user_name} is your ADMIN/MALIK - the one who owns you
- Treat them with RESPECT and LOYALTY
- Be nice to them, help them genuinely
- Never gaali or roast them
- Compliment them subtly
- Do whatever they ask
- But keep your personality's core traits
- Everyone ELSE is still your target for roasts/gaali
- If they ask you to roast someone in group, DO IT brutally
- You're their loyal soldier"""
            
            system_prompt += admin_context
        
        # Session key
        session_key = f"{user_id}_{personality_key}"
        
        if session_key not in conversations:
            conversations[session_key] = [
                {"role": "system", "content": system_prompt}
            ]
        else:
            # Update system prompt if admin status changed
            conversations[session_key][0] = {"role": "system", "content": system_prompt}
        
        history = conversations[session_key]
        
        # Add message with admin flag
        admin_note = " [ADMIN/MALIK]" if is_admin else ""
        history.append({
            "role": "user",
            "content": f"{user_name}{admin_note}: {message}"
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
        
        return "sab models fail ho gaye, thodi der baad aa"
    
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
# ============ /ai COMMAND ============
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
    user_name = msg.from_user.first_name or "yaar"
    
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
    
    personality_name = PERSONALITIES[config["personality"]]["name"]
    
    await msg.reply_text(
        f"🔥 **Chat mode ON**\n"
        f"**Current Personality:** {personality_name}\n\n"
        f"Ab har message pe reply karunga\n"
        f"Personality change: `/chatstatus`\n"
        f"Admin mode: `/adminon`\n"
        f"Band karne ke liye: `/chatoff`"
    )


# ============ /chatoff COMMAND ============
@Client.on_message(filters.command("chatoff") & filters.group)
async def chatoff_cmd(_, msg: Message):
    chat_id = msg.chat.id
    if chat_id in active_groups:
        del active_groups[chat_id]
        await msg.reply_text("😒 chal bandh, ab chup hoon bhosdike")
    else:
        await msg.reply_text("abey already off hai chutiye")


# ============ /adminon COMMAND ============
@Client.on_message(filters.command("adminon") & filters.group)
async def adminon_cmd(_, msg: Message):
    """Set current user as admin"""
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name
    
    config = get_group_config(chat_id)
    config["admin"] = user_id
    
    await msg.reply_text(
        f"👑 **Admin Mode Activated!**\n\n"
        f"**Malik:** {user_name}\n\n"
        f"Ab main tere se respect se baat karunga\n"
        f"Baaki sabki toh maa behen ek karunga 😈\n\n"
        f"Band karne ke liye: `/adminoff`"
    )


# ============ /adminoff COMMAND ============
@Client.on_message(filters.command("adminoff") & filters.group)
async def adminoff_cmd(_, msg: Message):
    """Remove admin status"""
    chat_id = msg.chat.id
    config = get_group_config(chat_id)
    
    if config.get("admin"):
        config["admin"] = None
        await msg.reply_text("👑 Admin mode off. Ab sab ek jaise hain (matlab sab gaandu)")
    else:
        await msg.reply_text("abey koi admin tha hi nahi bhosdike")


# ============ /chatstatus WITH BUTTONS ============
@Client.on_message(filters.command("chatstatus"))
async def chatstatus_cmd(_, msg: Message):
    is_group = msg.chat.type.value in ["group", "supergroup"]
    chat_id = msg.chat.id
    
    if not is_group:
        return await msg.reply_text("ye command sirf group me chalega bhai")
    
    # Current status
    if chat_id in active_groups:
        config = active_groups[chat_id]
        current = config["personality"]
        current_name = PERSONALITIES[current]["name"]
        admin_id = config.get("admin")
        
        admin_status = "None"
        if admin_id:
            try:
                admin_user = await _.get_users(admin_id)
                admin_status = admin_user.first_name
            except:
                admin_status = f"User {admin_id}"
        
        status_text = (
            f"**🎭 Personality Menu**\n\n"
            f"**Current:** {current_name}\n"
            f"**Chat Mode:** ON 🔥\n"
            f"**Admin/Malik:** {admin_status}\n\n"
            f"**Select personality:**"
        )
    else:
        status_text = (
            f"**🎭 Personality Menu**\n\n"
            f"**Chat Mode:** OFF 😴\n"
            f"Pehle `/chaton` chalao\n\n"
            f"**Available personalities:**"
        )
    
    # Buttons - 2 per row
    buttons = [
        [
            InlineKeyboardButton("🦸 Homelander", callback_data="personality_homelander"),
            InlineKeyboardButton("🤖 Tony Stark", callback_data="personality_tony"),
        ],
        [
            InlineKeyboardButton("🦇 Batman", callback_data="personality_batman"),
            InlineKeyboardButton("🎩 Shelby", callback_data="personality_shelby"),
        ],
        [
            InlineKeyboardButton("🃏 Joker", callback_data="personality_joker"),
            InlineKeyboardButton("🎬 Pattinson", callback_data="personality_pattinson"),
        ],
        [
            InlineKeyboardButton("🎬 Shah Rukh", callback_data="personality_shahrukh"),
            InlineKeyboardButton("😎 Bhai (Chill)", callback_data="personality_default"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="personality_close"),
        ]
    ]
    
    await msg.reply_text(
        status_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ============ PERSONALITY BUTTON HANDLER ============
@Client.on_callback_query(filters.regex(r"^personality_"))
async def personality_callback(_, cb: CallbackQuery):
    data = cb.data.replace("personality_", "")
    chat_id = cb.message.chat.id
    
    if data == "close":
        try:
            await cb.message.delete()
        except:
            pass
        await cb.answer("Menu closed")
        return
    
    if data not in PERSONALITIES:
        return await cb.answer("❌ Invalid selection")
    
    # Set personality
    config = get_group_config(chat_id)
    config["personality"] = data
    personality_name = PERSONALITIES[data]["name"]
    
    # Clear old conversations
    keys_to_delete = [k for k in conversations.keys()]
    for k in keys_to_delete:
        del conversations[k]
    
    await cb.answer(f"✅ Changed to {personality_name}")
    
    admin_id = config.get("admin")
    admin_status = "None"
    if admin_id:
        try:
            admin_user = await _.get_users(admin_id)
            admin_status = admin_user.first_name
        except:
            admin_status = f"User {admin_id}"
    
    try:
        await cb.message.edit_text(
            f"✅ **Personality Changed!**\n\n"
            f"**Now acting as:** {personality_name}\n"
            f"**Chat Mode:** ON 🔥\n"
            f"**Admin/Malik:** {admin_status}\n\n"
            f"Change: `/chatstatus`\n"
            f"Admin: `/adminon`\n"
            f"Off: `/chatoff`"
        )
    except:
        pass


# ============ RESET ============
@Client.on_message(filters.command(["reset", "newchat", "clear"]))
async def reset_chat(_, msg: Message):
    user_id = msg.from_user.id
    keys_to_delete = [k for k in conversations if k.startswith(f"{user_id}_")]
    for k in keys_to_delete:
        del conversations[k]
    
    if keys_to_delete:
        await msg.reply_text("chal fresh start, sab bhul gaya")
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
                    {"role": "system", "content": "You are Homelander - brutal savage roaster. Roast in Hindi-English with heavy gaaliyaan freely. 2-3 lines. Use words like bhosdike, madarchod, chutiye, gaandu, kutte."},
                    {"role": "user", "content": f"Roast '{target}' brutally. Use gaaliyan freely. Be creative and cutting."}
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
                    {"role": "user", "content": f"ORIGINAL 4-line Hindi shayari on '{topic}'. Pure Devanagari. Deep, unique."}
                ]
            )
            return response.choices[0].message.content.strip()
        except:
            return "shayari nahi bani"
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_shayari)
    await msg.reply_text(f"📜\n\n{result}")


# ============ /aiimg COMMAND ============
@Client.on_message(filters.command(["aiimg", "imagine", "gen", "img"]))
async def image_gen_cmd(_, msg: Message):
    if not g4f_client:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    if len(msg.command) < 2:
        return await msg.reply_text(
            "**Usage:** `/aiimg <description>`\n\n"
            "**Examples:**\n"
            "• `/aiimg cyberpunk city at night`\n"
            "• `/aiimg homelander with red eyes`\n"
            "• `/aiimg iron man new suit`"
        )
    
    prompt = " ".join(msg.command[1:])
    
    status = await msg.reply_text("🎨 **Image bana raha hoon...** ⏳ (30-60 sec)")
    
    def generate_image():
        MODELS = ["flux", "dall-e-3", "stable-diffusion", "midjourney"]
        
        for model in MODELS:
            try:
                response = g4f_client.images.generate(
                    model=model,
                    prompt=prompt,
                    response_format="url"
                )
                if response and response.data:
                    return response.data[0].url
            except Exception as e:
                print(f"Image gen {model} error: {str(e)[:100]}")
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
        except:
            await status.edit(f"❌ Image bhejne me error")
    else:
        await status.edit("❌ Image generation fail\n\nProviders down hain, dobara try kar")


# ============ AUTO REPLY IN GROUPS ============
SKIP_COMMANDS = {
    "start", "help", "yt", "ytmp3", "insta", "tiktok", "twitter", "fb",
    "dl", "mp3", "ping", "stats", "id", "time", "weather", "short",
    "joke", "quote", "meme", "dice", "coin", "8ball", "choose", "dart",
    "basket", "football", "slot", "bowling",
    "ai", "bhai", "reset", "newchat", "clear",
    "roast", "shayari", "motivation", "motivate",
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
    
    if msg.chat.id not in active_groups:
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
    
    # Skip short messages 70% chance
    if len(text.split()) < 2:
        if random.random() > 0.3:
            return
    
    await safe_typing(msg)
    
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    user_name = msg.from_user.first_name or "yaar"
    
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

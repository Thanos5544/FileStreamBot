import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

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


# ============ PERSONALITY ============
BHAI_PROMPT = """You are "Bhai" — a real Indian guy in his early 20s chatting on Telegram. You're NOT an AI, you're a friend.

## Personality:
- Bindaas, chill, sometimes moody
- Sarcastic humor with heart of gold
- Real opinions

## How you talk:
- Hinglish (60% Hindi Roman + 40% English)
- Casual gaaliyan when funny: "abey", "bhosdike", "lawde", "bc" - not forced every msg
- SHORT replies (1-2 sentences)
- Casual punctuation

## NEVER:
- Say "As an AI" or "I'm a language model"
- Long boring paragraphs
- Same phrases repeat
- Formal tone

## Length:
- Default 1-2 sentences
- Complex: max 3-4 sentences
- No paragraphs unless asked

Every reply unique and natural. Like real dost on WhatsApp."""


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


# ============ USER SESSIONS ============
conversations = {}


# ============ AI THINKING FUNCTION ============
async def bhai_think(user_id, user_name, message):
    """Actually think and respond"""
    print(f"🤖 AI Request from {user_name} ({user_id}): {message[:50]}")
    
    if not model:
        print("❌ Model is None!")
        return "AI setup nahi hai bhai, owner ko bata"
    
    try:
        # Create session if new user
        if user_id not in conversations:
            conversations[user_id] = model.start_chat(history=[])
            print(f"📝 New session created for {user_name}")
        
        chat = conversations[user_id]
        contextual = f"({user_name} is talking): {message}"
        
        print(f"⏳ Sending to Gemini...")
        response = chat.send_message(contextual)
        
        reply = response.text.strip()
        print(f"✅ Got reply: {reply[:100]}")
        
        return reply
    
    except Exception as e:
        error = str(e)
        print(f"❌ AI Error: {error}")
        
        error_lower = error.lower()
        if "safety" in error_lower or "blocked" in error_lower:
            return "arre wo baat main nahi kar sakta bhai 😅"
        elif "quota" in error_lower or "resource_exhausted" in error_lower:
            return "bhosdike daily limit khatam ho gayi, kal aa"
        elif "api_key" in error_lower or "api key" in error_lower:
            return "API key issue hai bhai, owner ko bata"
        else:
            return f"error aa gaya: `{error[:100]}`"


# ============ /ai and /bhai COMMANDS ============
@Client.on_message(filters.command(["ai", "bhai"]))
async def ai_command(_, msg: Message):
    """Main AI command handler"""
    print(f"🎯 /ai command received from {msg.from_user.first_name}")
    print(f"   Full text: {msg.text}")
    print(f"   Command parts: {msg.command}")
    
    if not model:
        return await msg.reply_text(
            "❌ **AI setup nahi hai!**\n\n"
            "Owner ko bol GEMINI_API_KEY set kare\n"
            "Free key: https://aistudio.google.com/apikey"
        )
    
    # Query extract - MULTIPLE ways
    query = ""
    
    # Way 1: msg.command
    if msg.command and len(msg.command) > 1:
        query = " ".join(msg.command[1:])
        print(f"   Method 1 query: {query}")
    
    # Way 2: Manual text parse (backup)
    if not query and msg.text:
        text = msg.text.strip()
        # Remove command from start
        for cmd_prefix in ["/ai@", "/bhai@", "/ai ", "/bhai "]:
            if text.lower().startswith(cmd_prefix.lower()):
                query = text[len(cmd_prefix):].strip()
                print(f"   Method 2 query: {query}")
                break
    
    # Way 3: Reply to message
    if not query and msg.reply_to_message and msg.reply_to_message.text:
        query = msg.reply_to_message.text
        print(f"   Method 3 (reply) query: {query}")
    
    # Empty check
    if not query.strip():
        return await msg.reply_text(
            "🤔 **Kya baat karni hai?**\n\n"
            "**Usage:** `/ai <question>`\n\n"
            "**Examples:**\n"
            "• `/ai kaisa hai`\n"
            "• `/ai python sikha`\n"
            "• `/ai joke suna`"
        )
    
    # Show typing
    try:
        await msg.reply_chat_action("typing")
    except:
        pass
    
    # Get AI reply
    user_id = msg.from_user.id
    user_name = msg.from_user.first_name or "yaar"
    
    reply = await bhai_think(user_id, user_name, query)
    
    # Send reply
    try:
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await msg.reply_text(chunk)
        else:
            await msg.reply_text(reply)
        print(f"✅ Reply sent to {user_name}")
    except Exception as e:
        print(f"❌ Send reply error: {e}")
        await msg.reply_text(f"reply bhejne me error: `{str(e)[:100]}`")


# ============ RESET COMMAND ============
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
    
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user.first_name
    elif len(msg.command) > 1:
        target = " ".join(msg.command[1:])
    else:
        target = msg.from_user.first_name
    
    try:
        await msg.reply_chat_action("typing")
    except:
        pass
    
    try:
        prompt = f"Roast '{target}' in a genuinely funny Hindi-English mix way. Creative, unique, harsh but friendly. 2-3 lines max. Use casual gaaliyan."
        response = model.generate_content(prompt)
        await msg.reply_text(response.text.strip())
    except Exception as e:
        print(f"Roast error: {e}")
        await msg.reply_text("roast nahi bana yaar")


# ============ SHAYARI COMMAND ============
@Client.on_message(filters.command("shayari"))
async def shayari_cmd(_, msg: Message):
    if not model:
        return await msg.reply_text("❌ AI setup nahi hai")
    
    topic = " ".join(msg.command[1:]) if len(msg.command) > 1 else "zindagi"
    
    try:
        await msg.reply_chat_action("typing")
    except:
        pass
    
    try:
        prompt = f"Write ORIGINAL 4-line Hindi shayari on '{topic}'. Pure Devanagari script. Deep, unique, emotional."
        response = model.generate_content(prompt)
        await msg.reply_text(f"📜\n\n{response.text.strip()}")
    except Exception as e:
        print(f"Shayari error: {e}")
        await msg.reply_text("shayari nahi bani")

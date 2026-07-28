"""
REAL AI Chatbot - Google Gemini
Actually thinks like ChatGPT!
"""

from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import os

# GEMINI API KEY - Environment variable se lo ya direct paste
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"


# ==================== REAL AI CHAT ====================

@Client.on_message(filters.command(["ai", "ask", "gemini"]) & filters.private)
async def real_ai_chat(client: Client, message: Message):
    """Real AI that actually thinks!"""
    
    # Get question
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply_text(
            "**🤖 Real AI Chatbot**\n\n"
            "**Usage:**\n"
            "`/ai <question>`\n\n"
            "**Example:**\n"
            "`/ai Explain quantum physics in Hindi`\n"
            "`/ai Write a poem about coding`\n\n"
            "💡 I actually think - not pre-written! 🧠"
        )
    
    if message.reply_to_message:
        question = message.reply_to_message.text or "This"
    else:
        question = message.text.split(maxsplit=1)[1]
    
    status = await message.reply_text("🤔 **Thinking...**")
    
    try:
        # Get AI response from Gemini
        response = await get_gemini_response(question)
        
        if response:
            # Split if too long (Telegram limit)
            if len(response) > 4000:
                # Split into chunks
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                
                await status.edit_text(f"**🤖 AI Response:**\n\n{chunks[0]}")
                
                # Send remaining chunks
                for chunk in chunks[1:]:
                    await message.reply_text(chunk)
            else:
                await status.edit_text(f"**🤖 AI Response:**\n\n{response}")
        else:
            await status.edit_text(
                "❌ AI response nahi mila!\n\n"
                "API key check karo ya phir se try karo!"
            )
        
    except Exception as e:
        await status.edit_text(f"❌ Error: {str(e)[:200]}")


# ==================== CASUAL CHAT WITH AI ====================

@Client.on_message(filters.text & filters.private & ~filters.command(["start", "help", "ytlink", "ythelp"]))
async def auto_ai_chat(client: Client, message: Message):
    """Auto respond to any text with AI"""
    
    text = message.text
    
    # Ignore if too short
    if len(text) < 3:
        return
    
    # Show typing
    await client.send_chat_action(message.chat.id, "typing")
    
    try:
        # Add personality prompt
        prompt = f"Reply in casual Hinglish (Hindi + English mix) style like a friendly bro. Keep it short and use emojis. Question: {text}"
        
        response = await get_gemini_response(prompt)
        
        if response:
            await message.reply_text(response)
        
    except:
        pass  # Silently fail for casual chat


# ==================== GEMINI API FUNCTION ====================

async def get_gemini_response(prompt: str) -> str:
    """Get response from Google Gemini AI"""
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GEMINI_API,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract response text
                    try:
                        response = data['candidates'][0]['content']['parts'][0]['text']
                        return response.strip()
                    except (KeyError, IndexError):
                        return None
                else:
                    error_text = await resp.text()
                    print(f"Gemini API error: {error_text}")
                    return None
                
    except Exception as e:
        print(f"Gemini request error: {e}")
        return None


# ==================== SPECIAL AI COMMANDS ====================

@Client.on_message(filters.command("explain"))
async def ai_explain(client: Client, message: Message):
    """Explain anything in simple terms"""
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/explain <topic>`")
    
    topic = message.text.split(maxsplit=1)[1]
    status = await message.reply_text("📚 Explaining...")
    
    prompt = f"Explain '{topic}' in simple Hinglish (Hindi + English mix) that a beginner can understand. Use examples and emojis."
    
    response = await get_gemini_response(prompt)
    
    if response:
        await status.edit_text(f"**📚 Explanation:**\n\n{response}")
    else:
        await status.edit_text("❌ Failed to explain!")


@Client.on_message(filters.command("code"))
async def ai_code(client: Client, message: Message):
    """Generate code"""
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/code <what to code>`")
    
    requirement = message.text.split(maxsplit=1)[1]
    status = await message.reply_text("💻 Generating code...")
    
    prompt = f"Write Python code for: {requirement}. Include comments in Hinglish. Make it simple and working."
    
    response = await get_gemini_response(prompt)
    
    if response:
        await status.edit_text(f"**💻 Code:**\n\n```python\n{response}\n```")
    else:
        await status.edit_text("❌ Failed to generate code!")


@Client.on_message(filters.command("translate"))
async def ai_translate(client: Client, message: Message):
    """Translate text"""
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/translate <text>`")
    
    text = message.text.split(maxsplit=1)[1]
    status = await message.reply_text("🌐 Translating...")
    
    prompt = f"Translate this to Hindi (Devanagari script): {text}"
    
    response = await get_gemini_response(prompt)
    
    if response:
        await status.edit_text(f"**🌐 Translation:**\n\n{response}")
    else:
        await status.edit_text("❌ Translation failed!")


@Client.on_message(filters.command("summarize"))
async def ai_summarize(client: Client, message: Message):
    """Summarize text"""
    
    if not message.reply_to_message:
        return await message.reply_text("Reply to a long message with `/summarize`")
    
    text = message.reply_to_message.text or message.reply_to_message.caption
    
    if not text or len(text) < 100:
        return await message.reply_text("Text too short to summarize!")
    
    status = await message.reply_text("📝 Summarizing...")
    
    prompt = f"Summarize this in 2-3 lines in Hinglish: {text}"
    
    response = await get_gemini_response(prompt)
    
    if response:
        await status.edit_text(f"**📝 Summary:**\n\n{response}")
    else:
        await status.edit_text("❌ Summarization failed!")


# ==================== HELP ====================

@Client.on_message(filters.command("aihelp"))
async def ai_help(client: Client, message: Message):
    """AI commands help"""
    
    help_text = (
        "**🤖 Real AI Chatbot - Commands**\n\n"
        "**Basic:**\n"
        "`/ai <question>` - Ask anything\n"
        "`/ask <question>` - Same as /ai\n\n"
        "**Special:**\n"
        "`/explain <topic>` - ELI5 explanation\n"
        "`/code <requirement>` - Generate code\n"
        "`/translate <text>` - Translate to Hindi\n"
        "`/summarize` - Summarize (reply to msg)\n\n"
        "**Examples:**\n"
        "`/ai Quantum computing kya hai?`\n"
        "`/code Create a calculator`\n"
        "`/explain Blockchain`\n\n"
        "**Auto Chat:**\n"
        "Just message me anything - I'll reply!\n\n"
        "🧠 **I actually think - powered by Google Gemini!**"
    )
    
    await message.reply_text(help_text)


print("✅ Real AI Chatbot (Google Gemini) Loaded! 🧠")

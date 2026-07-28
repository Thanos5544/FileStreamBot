"""
REAL AI Chatbot - Google Gemini (Fixed!)
"""

from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import os
import json

# API KEY - Yaha paste karo temporarily test ke liye
GEMINI_API_KEY = "AQ.Ab8RN6JtDTLBhnJkymAq_tdQs_Gle8KTaFwzoXjkqkq_bQ-g-w"  # ← YAHA PASTE KARO!

# Ya environment variable se
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# ==================== MAIN AI COMMAND ====================

@Client.on_message(filters.command(["ai", "ask"]) & filters.private)
async def ai_chat(client: Client, message: Message):
    """Real AI Chat"""
    
    # Check API key
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        return await message.reply_text(
            "❌ **API Key not configured!**\n\n"
            "Admin: Add GEMINI_API_KEY in environment variables!"
        )
    
    # Get question
    if len(message.command) < 2:
        return await message.reply_text(
            "**🤖 AI Chatbot**\n\n"
            "Usage: `/ai <question>`\n\n"
            "Example:\n"
            "`/ai Explain AI in Hindi`"
        )
    
    question = message.text.split(maxsplit=1)[1]
    status = await message.reply_text("🤔 Thinking...")
    
    try:
        # Get AI response
        response = await ask_gemini(question)
        
        if response:
            # Handle long responses
            if len(response) > 4000:
                chunks = [response[i:i+3900] for i in range(0, len(response), 3900)]
                await status.edit_text(f"**🤖 AI:**\n\n{chunks[0]}")
                for chunk in chunks[1:]:
                    await message.reply_text(chunk)
            else:
                await status.edit_text(f"**🤖 AI:**\n\n{response}")
        else:
            await status.edit_text(
                "❌ **No response!**\n\n"
                "Check:\n"
                "• API key valid hai?\n"
                "• Internet working?\n"
                "• Try again!"
            )
        
    except Exception as e:
        await status.edit_text(f"❌ **Error:**\n```{str(e)[:200]}```")


# ==================== GEMINI API ====================

async def ask_gemini(prompt: str) -> str:
    """Call Gemini API"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1000
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                
                # Debug log
                print(f"Gemini API Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract text
                    try:
                        text = data['candidates'][0]['content']['parts'][0]['text']
                        return text.strip()
                    except (KeyError, IndexError) as e:
                        print(f"Parse error: {e}")
                        print(f"Response: {data}")
                        return None
                
                else:
                    # Error details
                    error_text = await resp.text()
                    print(f"API Error {resp.status}: {error_text}")
                    return None
        
    except Exception as e:
        print(f"Request failed: {e}")
        return None


# ==================== TEST COMMAND ====================

@Client.on_message(filters.command("aitest"))
async def test_ai(client: Client, message: Message):
    """Test if AI is working"""
    
    status = await message.reply_text("🧪 Testing AI...")
    
    # Check API key
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        return await status.edit_text(
            "❌ **API Key Missing!**\n\n"
            "Steps:\n"
            "1. Go to: aistudio.google.com/app/apikey\n"
            "2. Create API key\n"
            "3. Add to bot config"
        )
    
    # Test request
    test_response = await ask_gemini("Say 'Hello' in Hindi")
    
    if test_response:
        await status.edit_text(
            f"✅ **AI Working!**\n\n"
            f"**Test Response:**\n{test_response}\n\n"
            f"**API Key:** {GEMINI_API_KEY[:20]}...\n"
            f"**Status:** Active ✅"
        )
    else:
        await status.edit_text(
            "❌ **AI Not Working!**\n\n"
            "**Possible issues:**\n"
            "• Invalid API key\n"
            "• API quota exceeded\n"
            "• Network issue\n\n"
            "**API Key (first 20 chars):**\n"
            f"`{GEMINI_API_KEY[:20]}...`"
        )


# ==================== SIMPLE COMMANDS ====================

@Client.on_message(filters.command("explain"))
async def explain(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/explain <topic>`")
    
    topic = message.text.split(maxsplit=1)[1]
    status = await message.reply_text("📚 Explaining...")
    
    prompt = f"Explain '{topic}' in simple Hindi/Hinglish for beginners with examples and emojis"
    response = await ask_gemini(prompt)
    
    if response:
        await status.edit_text(f"**📚 Explanation:**\n\n{response}")
    else:
        await status.edit_text("❌ Failed!")


@Client.on_message(filters.command("aihelp"))
async def ai_help(client: Client, message: Message):
    help_text = (
        "**🤖 AI Commands**\n\n"
        "`/ai <question>` - Ask anything\n"
        "`/explain <topic>` - Get explanation\n"
        "`/aitest` - Test if AI working\n"
        "`/aihelp` - This help\n\n"
        "**Example:**\n"
        "`/ai What is Python?`\n\n"
        "**Powered by Google Gemini** 🧠"
    )
    await message.reply_text(help_text)


print("✅ Real AI Chatbot Loaded!")

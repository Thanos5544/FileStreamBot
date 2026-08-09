"""
HDQWalls Wallpaper Downloader Plugin
Commands: 
  /wall <search>     - Search & download wallpaper
  /4k <query>        - Same as above

Features:
✅ Scrapes hdqwalls.com
✅ Shows Preview first
✅ Two buttons: Original + Optimized
✅ Auto sends to chat
"""

import io
import os
import re
import asyncio
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    CallbackQuery
)

# Config
TEMP_FOLDER = "temp/wallpapers"
Path(TEMP_FOLDER).mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

BASE_URL = "https://hdqwalls.com"


class HDQWallsScraper:
    """HDQWalls.com Scraper Class"""
    
    @staticmethod
    def search(query: str, limit: int = 6):
        """
        Search wallpapers on HDQWalls
        
        Returns list of dicts:
        [
            {
                'title': 'Iron Man 4K',
                'url': '/wallpaper/iron-man-4k',
                'image_url': 'https://...jpg',      # Preview image
                'original_url': 'https://...jpg',   # Full resolution
                'resolution': '3840x2160',
                'size': '1.19MB'
            }
        ]
        """
        try:
            search_url = f"{BASE_URL}/wallpapers/{quote_plus(query)}"
            print(f"[HDQWalls] Searching: {search_url}")
            
            response = requests.get(search_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find wallpaper items (adjust based on actual site structure)
            # HDQWalls uses specific class names
            items = soup.find_all('div', class_='wallpaper-item') or \
                   soup.find_all('article') or \
                   soup.find_all('a', href=re.compile(r'/wallpaper/'))
            
            if not items items:
                # Fallback: find all image links
                items = soup.find_all('img', src=re.compile(r'hdqwalls'))
            
            count = 0
            seen_urls = set()
            
            for item in items[:limit*2]:  # Get extra to filter duplicates
                try:
                    # Extract link
                    if item.name == 'a':
                        link = item.get('href')
                        img_tag = item.find('img')
                    elif item.name == 'img':
                        link = item.parent.get('href') if item.parent else None
                        img_tag = item
                    else:
                        link = item.find('a', href=True)
                        if link:
                            link = link['href']
                        img_tag = item.find('img')
                    
                    if not link or link in seen_urls:
                        continue
                    
                    seen_urls.add(link)
                    
                    # Get full URL
                    full_link = urljoin(BASE_URL, link)
                    
                    # Get preview image
                    preview_src = img_tag.get('src') or img_tag.get('data-src') if img_tag else None
                    if preview_src and not preview_src.startswith('http'):
                        preview_src = urljoin(BASE_URL, preview_src)
                    
                    # Get title from alt text or nearby text
                    title = img_tag.get('alt', '') if img_tag else ''
                    if not title:
                        title_text = item.find('h3') or item.find('h2') or item.find('span', class_='title')
                        title = title_text.get_text(strip=True) if title_text else query
                    
                    if not title:
                        continue
                    
                    # Visit individual page to get download links
                    dl_info = HDQWallsScraper._get_download_links(full_link)
                    
                    results.append({
                        'title': title,
                        'page_url': full_link,
                        'preview_url': preview_src,
                        **dl_info
                    })
                    
                    count += 1
                    if count >= limit:
                        break
                        
                except Exception as e:
                    continue
            
            return results if results else None
            
        except Exception as e:
            print(f"[HDQWalls] Search Error: {e}")
            return None
    
    @staticmethod
    def _get_download_links(page_url: str):
        """
        Visit wallpaper page and extract download links
        Returns: {'original_url': ..., 'mobile_url': ..., ...}
        """
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            info = {
                'original_url': None,
                'optimized_url': None,
                'resolution': 'Unknown',
                'size': 'Unknown'
            }
            
            # Find download buttons/links
            # HDQWalls usually has specific patterns
            links = soup.find_all('a', href=re.compile(r'\.(jpg|jpeg|png)', re.I))
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                if not href.startswith('http'):
                    href = urljoin(BASE_URL, href)
                
                # Identify based on text content
                if 'original' in text or (not info['original_url']):
                    info['original_url'] = href
                
                if 'download' in text or '1080' in text or '2400' in text:
                    info['optimized_url'] = href
            
            # Extract meta info
            res_match = re.search(r'(\d{3,4}x\d{3,4})', resp.text)
            if res_match:
                info['resolution'] = res_match.group(1)
            
            size_match = re.search(r'(\d+\.?\d*\s*MB)', resp.text, re.I)
            if size_match:
                info['size'] = size_match.group(1)
            
            # If still no direct URLs found, use og:image or main image
            if not info['original_url']:
                og_img = soup.find('meta', property='og:image')
                if og_img:
                    info['original_url'] = og_img.get('content')
                    info['preview_url'] = og_img.get('content')
            
            return info
            
        except Exception as e:
            print(f"Page parse error: {e}")
            return {'original_url': page_url, 'optimized_url': page_url}
    
    @staticmethod
    def optimize_for_mobile(image_path: str, max_size_kb: int = 2000):
        """
        Compress/resize image for mobile (Telegram friendly)
        Target: Under 2MB, good quality
        """
        try:
            img = Image.open(image_path)
            
            # Resize if too big (keep aspect ratio)
            max_dimension = 1920  # For mobile
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.LANCZOS)
            
            # Convert to RGB if necessary (remove alpha)
            if img.mode in ('RGBA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Optimize JPEG
            output = io.BytesIO()
            quality = 85
            while True:
                output.truncate(0)
                output.seek(0)
                img.save(output, format='JPEG', quality=quality, optimize=True)
                
                size_kb = len(output.getvalue()) / 1024
                if size_kb <= max_size_kb or quality <= 50:
                    break
                quality -= 10
            
            output.seek(0)
            return output, f"{img.size[0]}x{img.size[1]}"
            
        except Exception as e:
            return None, str(e)


# User session storage
wall_sessions = {}


@Client.on_message(filters.command(["wall", "4k", "wallpaper"]) & filters.private)
async def wall_command(client: Client, message: Message):
    """
    Command: /wall <search_query>
    Example: /4k iron man
             /wall nature
    """
    
    # Get query
    try:
        query = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    except:
        query = ""
    
    if not query:
        await message.reply_text(
            "🖼️ **HDQWalls Downloader**\n\n"
            "**Usage:**\n"
            "`/wall iron man`\n"
            "`/4k anime girl`\n"
            "`/wallpaper nature 4k`\n\n"
            "**Features:**\n"
            "• High Quality 4K Wallpapers\n"
            "• Direct from HDQWalls.com\n"
            "• Original + Mobile Optimized",
            parse_mode='markdown'
        )
        return
    
    searching_msg = await message.reply_text(f"🔍 Searching **{query}** on HDQWalls...")
    
    # Scrape
    scraper = HDQWallsScraper()
    results = scraper.search(query, limit=5)
    
    if not results:
        await searching_msg.edit_text(
            f"❌ No wallpapers found for **{query}**\n\nTry different keywords:\n"
            "`Batman`, `Nature`, `Cyberpunk`, `Abstract`",
            parse_mode='markdown'
        )
        return
    
    # Store session
    user_id = message.from_user.id
    wall_sessions[user_id] = {
        'results': results,
        'index': 0,
        'query': query
    }
    
    # Send first result with keyboard
    await _send_wallpaper_result(client, message, user_id, 0)
    await searching_msg.delete()


async def _send_wallpaper_result(client, msg_or_callback, user_id, index):
    """
    Helper to send/reply with wallpaper preview + buttons
    """
    session = wall_sessions.get(user_id)
    if not session:
        return
    
    results = session['results']
    if index >= len(results):
        index = 0
    if index < 0:
        index = len(results) - 1
    
    data = results[index]
    session['index'] = index
    
    # Prepare caption
    caption = (
        f"🖼️ **{data['title']}**\n\n"
        f"📐 Resolution: `{data.get('resolution', 'N/A')}`\n"
        f"📦 Size: `{data.get('size', 'N/A')}`\n"
        f"🌐 Source: [HDQWalls]({data['page_url']})\n\n"
        f"__Select option below 👇__"
    )
    
    # Create navigation + action buttons
    total = len(results)
    current = index + 1
    
    buttons = [
        [
            InlineKeyboardButton(f"◀ Prev", callback_data=f"wall_prev_{index}"),
            InlineKeyboardButton(f"{current}/{total}", callback_data="wall_info"),
            InlineKeyboardButton(f"Next ▶", callback_data=f"wall_next_{index}")
        ],
        [
            InlineKeyboardButton("⚡ Mobile Optimized", callback_data=f"wall_mobile_{index}"),
            InlineKeyboardButton("📥 Original 4K", callback_data=f"wall_original_{index}")
        ]
    ]
    
    markup = InlineKeyboardMarkup(buttons)
    
    # Send/Update with preview image
    preview_url = data.get('preview_url') or data.get('original_url')
    
    if preview_url:
        try:
            # Try to send as photo
            if isinstance(msg_or_callback, CallbackQuery):
                await msg_or_callback.message.delete()
                await client.send_photo(
                    chat_id=msg_or_callback.message.chat.id,
                    photo=preview_url,
                    caption=caption,
                    reply_markup=markup,
                    parse_mode='markdown'
                )
            else:
                await msg_or_callback.reply_photo(
                    photo=preview_url,
                    caption=caption,
                    reply_markup=markup,
                    parse_mode='markdown'
                )
            return
        except Exception as e:
            print(f"Photo send error: {e}, trying as text")
    
    # Fallback to text
    text_resp = (
        f"{caption}\n\n"
        f"⚠️ Preview unavailable. Use buttons below."
    )
    
    if isinstance(msg_or_callback, CallbackQuery):
        await msg_or_callback.edit_message_text(text_resp, reply_markup=markup, parse_mode='markdown')
    else:
        await msg_or_callback.reply_text(text_resp, reply_markup=markup, parse_mode='markdown')


@Client.on_callback_query(filters.regex(r"^wall_"))
async def wall_callbacks(client: Client, query: CallbackQuery):
    """
    Handle button clicks:
    - wall_prev_X, wall_next_X : Navigate
    - wall_mobile_X : Download compressed
    - wall_original_X : Download 4K original
    """
    user_id = query.from_user.id
    data_parts = query.data.split('_')
    action = data_parts[1]
    idx = int(data_parts[2]) if len(data_parts) > 2 else 0
    
    session = wall_sessions.get(user_id)
    if not session:
        await query.answer("Session expired! Search again.", show_alert=True)
        return
    
    if action == 'prev':
        new_idx = idx - 1
        await query.answer("Loading previous...")
        await _send_wallpaper_result(client, query, user_id, new_idx)
        
    elif action == 'next':
        new_idx = idx + 1
        await query.answer("Loading next...")
        await _send_wallpaper_result(client, query, user_id, new_idx)
        
    elif action == 'info':
        await query.answer(f"Wallpaper {idx+1} of {len(session['results'])}", show_alert=False)
        
    elif action == 'mobile':
        # Send optimized/compressed version
        await query.answer("⚡ Preparing optimized version...", show_alert=True)
        await _send_optimized(client, query, user_id, idx)
        
    elif action == 'original':
        # Send original 4K
        await query.answer("📥 Downloading 4K original...", show_alert=True)
        await _send_original(client, query, user_id, idx)


async def _send_optimized(client, callback, user_id, index):
    """
    Download original -> Resize -> Compress -> Send
    Target: Good quality, reasonable file size (<5MB for Telegram)
    """
    session = wall_sessions[user_id]
    data = session['results'][index]
    
    status_msg = await callback.message.reply_text("⏳ Downloading & optimizing for mobile...")
    
    try:
        url = data.get('original_url') or data.get('page_url')
        if not url:
            raise ValueError("No download URL found")
        
        # Download original
        tmp_file = f"{TEMP_FOLDER}/wall_orig_{user_id}_{index}.jpg"
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            raise ValueError(f"Download failed: {response.status_code}")
        
        with open(tmp_file, 'wb') as f:
            f.write(response.content)
        
        # Optimize
        opt_img, dims = HDQWallsScraper.optimize_for_mobile(tmp_file, max_size_kb=4000)
        
        if not opt_img:
            raise ValueError("Image optimization failed")
        
        # Cleanup temp
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        
        # Send optimized
        filename = f"{data['title'].replace('/', '_').replace(' ', '_')}_{dims}.jpg"
        
        await client.send_document(
            chat_id=callback.message.chat.id,
            document=opt_img,
            file_name=filename,
            caption=(
                f"✅ **Mobile Optimized Version**\n\n"
                f"🖼️ **{data['title']}**\n"
                f"📱 Resolution: `{dims}`\n"
                f"🔧 Compressed for Telegram\n\n"
                f"_For original click 4K button_"
            ),
            force_document=False  # Send as photo
        )
        
        await status_msg.delete()
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}\n\nYou can use this link directly:\n{data.get('page_url', 'N/A')}"
        await status_msg.edit_text(error_msg)


async def _send_original(client, callback, user_id, index):
    """
    Send original high-resolution wallpaper (may be large file)
    """
    session = wall_sessions[user_id]
    data = session['results'][index]
    
    status_msg = await callback.message.reply_text("⏳ Downloading 4K original...")
    
    try:
        url = data.get('original_url')
        if not url:
            raise ValueError("Original URL not available")
        
        # Download
        response = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        
        tmp_file = f"{TEMP_FOLDER}/wall_4k_{user_id}_{index}.jpg"
        
        with open(tmp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(tmp_file) / (1024*1024)  # MB
        
        # Check size limits (Telegram ~50MB for bots, but better keep <20MB for comfort)
        if file_size > 50:
            await status_msg.edit_text(
                f"⚠️ File is **{file_size:.1f}MB** (Too large!)\n\n"
                f"Use **Mobile Optimized** instead.\n\n"
                f"Or download directly:\n{data['page_url']}",
                parse_mode='markdown'
            )
            os.remove(tmp_file)
            return
        
        # Send as document (to preserve quality)
        filename = f"{data['title'].replace('/', '_')}_{data.get('resolution','4K')}.jpg"
        
        await client.send_document(
            chat_id=callback.message.chat.id,
            document=tmp_file,
            file_name=filename,
            caption=(
                f"📥 **Original 4K Wallpaper**\n\n"
                f"🖼️ **{data['title']}**\n"
                f"📐 Resolution: `{data.get('resolution', 'High Res')}`\n"
                f"📦 Size: `{file_size:.2f}MB`\n"
                f"🌐 Source: [HDQWalls](data.get('page_url'))"
            )
        )
        
        await status_msg.delete()
        os.remove(tmp_file)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Download failed: {str(e)}\n\nLink: {data.get('page_url')}")

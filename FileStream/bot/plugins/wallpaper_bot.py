"""
HDQWalls Wallpaper Downloader Plugin (FIXED VERSION)
Commands: /wall, /4k, /wallpaper
"""

import io
import os
import re
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

TEMP_FOLDER = "temp/wallpapers"
Path(TEMP_FOLDER).mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
BASE_URL = "https://hdqwalls.com"

class HDQWallsScraper:
    
    @staticmethod
    def search(query, limit=6):
        try:
            search_url = f"{BASE_URL}/wallpapers/{quote_plus(query)}"
            print(f"[HDQWalls] Searching: {search_url}")
            
            response = requests.get(search_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find wallpaper items
            items = soup.find_all('div', class_='wallpaper-item') or \
                   soup.find_all('article') or \
                   soup.find_all('a', href=re.compile(r'/wallpaper/'))
            
            if not items:
                # Fallback pattern
                items = soup.find_all('img', src=re.compile(r'hdqwalls|wallpaper'))
            
            count = 0
            seen_urls = set()
            
            for item in items[:limit*2]:
                try:
                    if item.name == 'a':
                        link = item.get('href')
                        img_tag = item.find('img')
                    elif item.name == 'img':
                        link = item.parent.get('href') if item.parent else None
                        img_tag = item
                    else:
                        link_tag = item.find('a', href=True)
                        link = link_tag['href'] if link_tag else None
                        img_tag = item.find('img')
                    
                    if not link or link in seen_urls or not img_tag:
                        continue
                    
                    seen_urls.add(link)
                    
                    full_link = urljoin(BASE_URL, link)
                    preview_src = img_tag.get('src') or img_tag.get('data-src')
                    if preview_src and not preview_src.startswith('http'):
                        preview_src = urljoin(BASE_URL, preview_src)
                    
                    title = img_tag.get('alt', '')
                    if not title:
                        t = item.find('h3') or item.find('h2')
                        title = t.get_text(strip=True) if t else query
                    
                    if not title:
                        continue
                    
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
            print(f"[HDQWalls] Error: {e}")
            return None
    
    @staticmethod
    def _get_download_links(page_url):
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            info = {
                'original_url': None,
                'optimized_url': None,
                'resolution': 'Unknown',
                'size': 'Unknown'
            }
            
            links = soup.find_all('a', href=re.compile(r'\.(jpg|jpeg|png)', re.I))
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                if not href.startswith('http'):
                    href = urljoin(BASE_URL, href)
                
                if not info['original_url']:
                    info['original_url'] = href
                
                if 'download' in text or '1080' in text:
                    info['optimized_url'] = href
            
            res_match = re.search(r'(\d{3,4}x\d{3,4})', resp.text)
            if res_match:
                info['resolution'] = res_match.group(1)
            
            size_match = re.search(r'(\d+\.?\d*\s*MB)', resp.text, re.I)
            if size_match:
                info['size'] = size_match.group(1)
            
            if not info['original_url']:
                og_img = soup.find('meta', property='og:image')
                if og_img:
                    info['original_url'] = og_img.get('content')
            
            return info
            
        except Exception as e:
            return {'original_url': page_url, 'optimized_url': page_url}
    
    @staticmethod
    def optimize_for_mobile(image_path, max_size_kb=2000):
        try:
            img = Image.open(image_path)
            max_dimension = 1920
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.LANCZOS)
            
            if img.mode in ('RGBA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
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


wall_sessions = {}

@Client.on_message(filters.command(["wall", "4k", "wallpaper"]) & filters.private)
async def wall_command(client: Client, message: Message):
    try:
        query = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    except:
        query = ""
    
    if not query:
        await message.reply_text(
            "🖼️ **HDQWalls Downloader**\n\n"
            "**Usage:**\n"
            "`/wall iron man`\n"
            "`/4k anime girl`\n",
            parse_mode='markdown'
        )
        return
    
    searching_msg = await message.reply_text(f"🔍 Searching **{query}**...")
    
    scraper = HDQWallsScraper()
    results = scraper.search(query, limit=5)
    
    if not results:
        await searching_msg.edit_text(f"❌ No wallpapers found for **{query}**")
        return
    
    user_id = message.from_user.id
    wall_sessions[user_id] = {'results': results, 'index': 0, 'query': query}
    
    await _send_result(client, message, user_id, 0)
    await searching_msg.delete()


async def _send_result(client, msg, user_id, index):
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
    
    caption = (
        f"🖼️ **{data['title']}**\n\n"
        f"📐 Resolution: `{data.get('resolution', 'N/A')}`\n"
        f"📦 Size: `{data.get('size', 'N/A')}`\n\n"
        f"_Select option below 👇_"
    )
    
    total = len(results)
    buttons = [
        [
            InlineKeyboardButton("◀ Prev", callback_data=f"wp_{index-1}"),
            InlineKeyboardButton(f"{index+1}/{total}", callback_data="wp_info"),
            InlineKeyboardButton("Next ▶", callback_data=f"wp_{index+1}")
        ],
        [
            InlineKeyboardButton("⚡ Mobile", callback_data=f"wpmobile_{index}"),
            InlineKeyboardButton("📥 Original", callback_data=f"wporig_{index}")
        ]
    ]
    
    markup = InlineKeyboardMarkup(buttons)
    preview_url = data.get('preview_url') or data.get('original_url')
    
    if hasattr(msg, 'reply_photo'):
        await msg.reply_photo(photo=preview_url, caption=caption, reply_markup=markup, parse_mode='markdown')
    elif hasattr(msg, 'message'):
        await client.send_photo(chat_id=msg.chat.id, photo=preview_url, caption=caption, reply_markup=markup, parse_mode='markdown')


@Client.on_callback_query(filters.regex("^wp"))
async def wp_callbacks(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    parts = query.data.split('_')
    
    if user_id not in wall_sessions:
        await query.answer("Session expired!", show_alert=True)
        return
    
    action = parts[0].replace("wp", "")
    
    if action == 'info':
        await query.answer("Wallpaper Info", show_alert=False)
        return
    
    idx = int(parts[1]) if parts[1] else 0
    
    if action == '':
        # Navigation check removed for simplicity
        pass
    elif parts[0] == "wpmobile":
        await query.answer("Preparing mobile...")
        await _download_send(client, query, user_id, idx, mode="mobile")
        return
    elif parts[0] == "wporig":
        await query.answer("Downloading original...")
        await _download_send(client, query, user_id, idx, mode="original")
        return
    
    await query.answer()
    new_idx = idx
    try:
        if action == '-':
            new_idx -= 1
        elif action == '+':
            new_idx += 1
        
        results_len = len(wall_sessions[user_id]['results'])
        if new_idx < 0:
            new_idx = results_len - 1
        if new_idx >= results_len:
            new_idx = 0
            
        await _send_result(client, query, user_id, new_idx)
    except:
        pass


async def _download_send(client, callback, user_id, index, mode="mobile"):
    session = wall_sessions[user_id]
    data = session['results'][index]
    
    status = await callback.message.reply_text("⏳ Processing...")
    
    try:
        url = data.get('original_url') or data.get('page_url')
        
        tmp_file = f"{TEMP_FOLDER}/dl_{user_id}_{index}.jpg"
        response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        
        with open(tmp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        if mode == "mobile":
            opt_img, dims = HDQWallsScraper.optimize_for_mobile(tmp_file)
            if opt_img:
                filename = f"{data['title'][:30]}_mobile.jpg".replace("/", "_")
                await client.send_document(
                    chat_id=callback.message.chat.id,
                    document=opt_img,
                    file_name=filename,
                    caption=f"⚡ **Mobile Optimized**\n{dims}",
                    force_document=False
                )
            else:
                raise Exception("Optimization failed")
        else:
            file_size = os.path.getsize(tmp_file) / (1024*1024)
            filename = f"{data['title'][:30]}_4K.jpg".replace("/", "_")
            await client.send_document(
                chat_id=callback.message.chat.id,
                document=tmp_file,
                file_name=filename,
                caption=f"📥 **Original** ({file_size:.2f}MB)"
            )
        
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        await status.delete()
        
    except Exception as e:
        await status.edit_text(f"❌ Error: {str(e)}")

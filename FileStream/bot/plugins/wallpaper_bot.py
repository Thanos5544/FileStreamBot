"""
WALLPAPER BOT PLUGIN (FIXED - Download then Send)
Command: /wall <query>
"""

import io
import os
import re
import time
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
TEMP_DIR = "temp_wall"
Path(TEMP_DIR).mkdir(exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Referer': 'https://hdqwalls.com/',
}

class WallFetcher:
    """Robust Wallpaper Fetcher"""
    
    @staticmethod
    def search(query):
        """Search wallpapers - returns list of dicts"""
        print(f"[WALL] Searching: {query}")
        
        # Strategy 1: Direct scrape
        results = WallFetcher._scrape_hdqwalls(query)
        if results and len(results) > 0:
            return results
        
        # Strategy 2: Alternative sources if main fails
        print("[WALL] Main source failed, trying alternative...")
        results = WallFetcher._search_alternative(query)
        return results
    
    @staticmethod
    def _scrape_hdqwalls(query):
        """Scrape HDQWalls with multiple patterns"""
        results = []
        
        base = "https://hdqwalls.com"
        urls = [
            f"{base}/wallpapers/{quote_plus(query)}",
            f"{base}/category/{quote_plus(query)}",
        ]
        
        for url in urls:
            try:
                print(f"[WALL] Trying: {url}")
                r = requests.get(url, headers=HEADERS, timeout=15)
                
                if r.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # Pattern A: Look for figure/img tags (modern sites)
                figures = soup.find_all('figure') or soup.find_all('div', class_='post')
                
                # Pattern B: Image tags inside links
                if not figures:
                    links_with_imgs = soup.find_all('a', href=re.compile(r'/wallpaper'))
                    figures = [l for l in links_with_imgs if l.find('img')]
                
                # Pattern C: Just find all large images
                if not figures:
                    imgs = soup.find_all('img', src=re.compile(r'wallpaper|4k|hd', re.I))
                    figures = imgs
                
                seen = set()
                
                for item in figures[:15]:
                    try:
                        data = WallExtractor.extract(item, base)
                        
                        if not data['url'] or data['url'] in seen:
                            continue
                        if not data['title']:
                            continue
                        
                        seen.add(data['url'])
                        results.append(data)
                        
                        if len(results) >= 6:
                            break
                            
                    except Exception as e:
                        print(f"Item error: {e}")
                        continue
                
                if results:
                    break  # Found results, stop checking other URLs
                    
            except Exception as e:
                print(f"URL error: {e}")
                continue
        
        return results
    
    @staticmethod
    def _search_alternative(query):
        """Fallback using image search APIs or other methods"""
        results = []
        
        try:
            # Use Bing Images API (free, no key needed)
            api_url = f"https://www.bing.com/images/search?q={quote_plus(query + ' wallpaper 4k')}&first=1&count=6&format=json"
            
            headers = {'User-Agent': HEADERS['User-Agent']}
            r = requests.get(api_url, headers=headers, timeout=10)
            
            # Parse mediaurls from response
            matches = re.findall(r'"murl":"(https?://[^"]+\.jpg)"', r.text)
            
            for i, img_url in enumerate(matches[:6]):
                results.append({
                    'title': f"{query} Wallpaper {i+1}",
                    'page': img_url,
                    'preview': img_url,
                    'original': img_url,
                    'res': 'Unknown',
                    'source': 'Bing'
                })
                
        except Exception as e:
            print(f"Fallback err: {e}")
        
        return results


class WallExtractor:
    """Extract info from HTML element"""
    
    @staticmethod
    def extract(element, base_url=""):
        """
        Extract title, urls from various HTML structures
        """
        info = {
            'title': '',
            'page': '',
            'preview': '',
            'original': '',
            'res': '4K'
        }
        
        tag_name = element.name
        
        # Case 1: <a> tag containing <img>
        if tag_name == 'a':
            info['page'] = element.get('href', '')
            img = element.find('img')
            if img:
                info['title'] = img.get('alt', '') or ''
                info['preview'] = img.get('src', '') or img.get('data-src', '')
        
        # Case 2: <img> tag directly
        elif tag_name == 'img':
            info['title'] = element.get('alt', '') or ''
            info['preview'] = element.get('src', '') or element.get('data-src', '')
            
            # Check parent link
            parent = element.parent
            if parent and parent.name == 'a':
                info['page'] = parent.get('href', '')
            elif parent:
                grandparent = parent.parent
                if grandparent and grandparent.name == 'a':
                    info['page'] = grandparent.get('href', '')
        
        # Case 3: Container (div/figure/article)
        else:
            # Find first link
            a_tag = element.find('a', href=True)
            if a_tag:
                info['page'] = a_tag.get('href', '')
            
            # Find first image
            img_tag = element.find('img')
            if img_tag:
                info['title'] = img_tag.get('alt', '')
                info['preview'] = img_tag.get('src', '') or img_tag.get('data-src', '')
            
            # If no alt, look for h2/h3
            if not info['title']:
                heading = element.find(['h2', 'h3', 'h4'])
                if heading:
                    info['title'] = heading.get_text(strip=True)[:80]
        
        # Cleanup URLs
        for key in ['page', 'preview']:
            val = info[key]
            if val and not val.startswith('http'):
                info[key] = urljoin(base_url, val)
        
        # Set original (usually same as page or derived from page)
        if info['page'] and not info['original']:
            # Try to guess original image URL from page URL
            info['original'] = WallExtractor._guess_original(info['page'], base_url)
        elif info['preview'] and not info['original']:
            info['original'] = info['preview']
        
        return info
    
    @staticmethod
    def _guess_original(page_url, base):
        """Try to construct original image URL from page URL"""
        # Common pattern: /wallpaper/name -> /download/name or similar
        parsed = urlparse(page_url)
        path = parsed.path
        
        # Replace path segments
        replacements = ['/download/', '/full/', '/original/', '/4k/']
        
        for repl in replacements:
            candidate = urljoin(base, path.replace('/wallpaper', repl))
            # Quick check if accessible
            try:
                r = requests.head(candidate, headers=HEADERS, timeout=5)
                if r.headers.get('content-type','').startswith('image'):
                    return candidate
            except:
                continue
        
        # Fallback: assume page itself might be image or redirect
        return page_url
    
    @staticmethod
    def get_download_info(url):
        """Visit page to get actual download link"""
        try:
            r = requests.get(url, headers={**HEADERS, 'Accept': '*/*'}, 
                           allow_redirects=True, timeout=10)
            
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Look for og:image (most reliable)
            og = soup.find('meta', property='og:image')
            if og and og.get('content'):
                return og['content']
            
            # Look for actual image src in main content
            main_img = soup.find('img', id='wallpaper-image') or \
                       soup.find('img', class_='main-img')
            if main_img:
                return main_img.get('src', url)
            
            return url
            
        except:
            return url


def download_image(url, filename=None):
    """Download image to file, return path or None"""
    try:
        if not filename:
            filename = f"{TEMP_DIR}/img_{int(time.time())}.jpg"
        
        print(f"[DL] Downloading: {url[:50]}...")
        
        # Stream download with proper headers
        headers = {
            **HEADERS,
            'Accept': 'image/jpeg,image/png,image/webp,*/*'
        }
        
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()
        
        # Check content type
        ct = resp.headers.get('content-type', '')
        if not ct.startswith('image'):
            print(f"[DL] Not image: {ct}")
            return None
        
        with open(filename, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify it's a real image
        try:
            img = Image.open(filename)
            img.verify()  # Verify integrity
            size_kb = os.path.getsize(filename) / 1024
            print(f"[DL] Success: {size_kb:.0f}KB")
            return filename
        except Exception as e:
            print(f"[DL] Invalid image: {e}")
            os.remove(filename) if os.path.exists(filename) else None
            return None
            
    except Exception as e:
        print(f"[DL] Failed: {e}")
        return None


def compress_image(input_path, max_mb=2.0):
    """Compress for mobile, return BytesIO or None"""
    try:
        img = Image.open(input_path).convert("RGB")
        
        # Resize if too big
        max_dim = 1920
        ratio = min(max_dim/max(img.size), 1.0)
        if ratio < 1:
            w, h = img.size
            img = img.resize((int(w*ratio), int(h*r)), Image.LANCZOS)
        
        out = io.BytesIO()
        quality = 85
        
        while True:
            out.seek(0); out.truncate()
            img.save(out, format="JPEG", quality=quality, optimize=True)
            size_mb = len(out.getvalue()) / (1024*1024)
            
            if size_mb <= max_mb or quality <= 40:
                break
            quality -= 10
        
        out.seek(0)
        return out
        
    except Exception as e:
        print(f"Compress err: {e}")
        return None


# Session store
sessions = {}

@Client.on_message(filters.command(["wall", "4k"]) & filters.private)
async def wall_cmd(client, m):
    """Handle /wall command"""
    
    try:
        query = m.text.split(None, 1)[1].strip()
    except IndexError:
        query = ""
    
    if not query:
        await m.reply(
            "**🖼️ Wallpaper Bot**\n\n"
            "`/wall batman dark`\n"
            "`/4k iron man`\n"
            "`/wall nature`",
            parse_mode='markdown'
        )
        return
    
    wait_msg = await m.reply(f"🔍 **Searching:** `{query}`...")
    
    # Search
    fetcher = WallFetcher()
    results = fetcher.search(query)
    
    if not results or len(results) == 0:
        await wait_msg.edit_text(
            f"❌ **Not Found:**\n`{query}`\n\n"
            f"Try different keywords!",
            parse_mode='markdown'
        )
        return
    
    # Store session
    uid = m.from_user.id
    sessions[uid] = {
        'results': results,
        'index': 0,
        'query': query,
        'wait_msg_id': wait_msg.id
    }
    
    await display_result(client, uid, 0)


async def display_result(client, uid, index):
    """Display single result with buttons"""
    if uid not in sessions:
        return
    
    ses = sessions[uid]
    res = ses['results']
    
    # Bounds check
    index = index % len(res) if res else 0
    ses['index'] = index
    
    item = res[index]
    
    # Show status (don't delete yet!)
    status = await client.send_message(
        uid, 
        f"⏳ Loading preview... ({index+1}/{len(res)})"
    )
    
    try:
        # CRITICAL STEP: Download image FIRST!
        preview_url = item.get('preview') or item.get('original')
        
        if not preview_url:
            raise Exception("No image URL")
        
        local_path = download_image(preview_url)
        
        if not local_path:
            # Try with original URL
            orig = item.get('original') or item.get('page')
            if orig != preview_url:
                local_path = download_image(orig)
        
        if not local_path:
            raise Exception("Could not download image")
        
        # Now send the downloaded file
        caption = (
            f"**{item['title']}**\n\n"
            f"📐 Resolution: `{item.get('res', 'HD')}`\n"
            f"_Use buttons below to download_"
        )
        
        total = len(res)
        btns = [
            [
                InlineKeyboardButton(f"◀ {index}", callback_data=f"wprev_{uid}_{max(0,index-1)}"),
                InlineKeyboardButton(f"{index+1}/{total}", callback_data=f"winfo_{uid}"),
                InlineKeyboardButton(f"{min(index+1,total-1)} ▶", callback_data=f"wnext_{uid}_{min(total-1,index+1)}")
            ],
            [
                InlineKeyboardButton("⚡ Mobile", callback_data=f"wmob_{uid}_{index}"),
                InlineKeyboardButton("📥 Original", callback_data=f"worig_{uid}_{index}")
            ]
        ]
        
        # Send as photo (with downloaded file)
        with open(local_path, 'rb') as photo_file:
            msg = await client.send_photo(
                chat_id=uid,
                photo=photo_file,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(btns),
                parse_mode='markdown'
            )
        
        # Clean up temp file
        try:
            os.remove(local_path)
        except:
            pass
        
        # Delete status messages
        await status.delete()
        if ses.get('wait_msg_id'):
            try:
                await client.delete_messages(uid, ses['wait_msg_id'])
            except:
                pass
                
    except Exception as e:
        error_text = (
            f"⚠️ **Error loading preview**\n\n"
            f"`{str(e)[:100]}`\n\n"
            f"Title: {item['title']}\n"
            f"Link: [Click here]({item.get('page','#')})"
        )
        
        await status.edit_text(
            error_text,
            parse_mode='markdown',
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↻ Retry", callback_data=f"wretry_{uid}_{index}")]
            ])
        )


@Client.on_callback_query(re.compile("^w"))
async def wall_cb(c, q):
    """Handle button presses"""
    data = q.data.split('_')
    action = data[0].replace('w', '')  # prev, next, mob, orig, info, retry
    uid = int(data[1]) if len(data) > 1 else q.from_user.id
    idx = int(data[2]) if len(data) > 2 else 0
    
    if uid not in sessions:
        await q.answer("Session expired. /wall again.", show_alert=True)
        return
    
    await q.answer()  # Acknowledge immediately
    
    if action == 'info':
        await q.answer("Wallpaper Info", show_alert=False)
        return
    
    if action in ('prev', 'next'):
        current = sessions[uid]['index']
        total = len(sessions[uid]['results'])
        
        new_idx = current + (-1 if action=='prev' else 1)
        if new_idx < 0: new_idx = total - 1
        if new_idx >= total: new_idx = 0
        
        await display_result(c, uid, new_idx)
        
    elif action == 'mob':
        await dl_and_send(c, q, idx, mode='mobile')
        
    elif action == 'orig':
        await dl_and_send(c, q, idx, mode='original')
        
    elif action == 'retry':
        await display_result(c, uid, idx)


async def dl_and_send(c, cb, idx, mode='mobile'):
    """Download full image and send to user"""
    uid = cb.from_user.id
    ses = sessions[uid]
    item = ses['results'][idx]
    
    status = await c.send_message(cb.message.chat.id, 
                                  f"{'⚡ Compressing...' if mode=='mobile' else '📥 Downloading 4K...'}")
    
    try:
        url = item.get('original') or item.get('page')
        
        # Download original
        tmp_path = download_image(url, f"{TEMP_DIR}/dl_{uid}_{idx}.jpg")
        
        if not tmp_path:
            raise Exception("Download failed")
        
        sz_mb = os.path.getsize(tmp_path) / (1024*1024)
        
        if mode == 'mobile':
            compressed = compress_image(tmp_path, max_mb=3.0)
            
            if not compressed:
                raise Exception("Compression failed")
            
            fname = f"{item['title'][:25]}_mobile.jpg".replace('/','_').replace('\\','_')
            await c.send_document(
                uid,
                compressed,
                file_name=fname,
                caption=f"✅ Mobile Optimized\n🖼️ {item['title']}",
                force_document=False  # Send as photo
            )
        else:
            fname = f"{item['title'][:25]}_4k.jpg".replace('/','_').replace('\\','_')
            await c.send_document(
                uid,
                tmp_path,
                file_name=fname,
                caption=f"📥 Original ({sz_mb:.1f}MB)\n📐 {item.get('res','HD')}"
            )
        
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        
        await status.delete()
        
    except Exception as e:
        await status.edit_text(f"❌ {str(e)}")

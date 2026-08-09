"""
HDQWalls Wallpaper Downloader (FIXED WORKING VERSION)
Command: /wall <query>
"""

import io
import os
import re
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

TEMP = "temp/walls"
Path(TEMP).mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://hdqwalls.com/',
}

class WallScraper:
    
    @staticmethod
    def find_wallpapers(query, count=6):
        """
        Robust finder - tries multiple methods
        """
        results = []
        
        # Method 1: Direct category/search URL
        results = WallScraper._try_search_url(query, count)
        if results:
            return results
            
        # Method 2: Google Images fallback
        results = WallScraper._fallback_google(query, count)
        return results
    
    @staticmethod
    def _try_search_url(query, limit):
        """Try scraping HDQWalls directly"""
        try:
            # Try multiple URL patterns
            urls_to_try = [
                f"https://hdqwalls.com/wallpapers/{quote_plus(query)}",
                f"https://hdqwalls.com/wallpaper/{quote_plus(query)}",
                f"https://hdqwalls.com/search?query={quote_plus(query)}"
            ]
            
            for search_url in urls_to_try:
                print(f"[WALL] Trying: {search_url}")
                
                try:
                    resp = requests.get(search_url, headers=HEADERS, timeout=10)
                    if resp.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Pattern 1: Main wrapper
                    items = soup.select('div.wallpaper-entry') or \
                           soup.select('div.thumb') or \
                           soup.select('article') or \
                           soup.select('.wallpaper-item')
                    
                    # Pattern 2: Look for links containing /wallpaper/
                    if not items:
                        items = soup.find_all('a', href=re.compile(r'/wallpaper/[a-z0-9\-]+$', re.I))
                    
                    # Pattern 3: Look for images with wallpapers in alt
                    if not items:
                        items = soup.find_all('img', alt=re.compile(r'wallpaper|4k|hd', re.I))
                    
                    found = []
                    seen = set()
                    
                    for item in items[:20]:  # Check first 20
                        try:
                            link, title, thumb = WallScraper._extract_data(item)
                            if not link or link in seen:
                                continue
                            
                            seen.add(link)
                            dl = WallScraper._get_download_page(urljoin("https://hdqwalls.com", link))
                            
                            found.append({
                                'title': title,
                                'page': urljoin("https://hdqwalls.com", link),
                                'preview': thumb,
                                **dl
                            })
                            
                            if len(found) >= limit:
                                break
                        except:
                            continue
                    
                    if found:
                        print(f"[WALL] Found {len(found)} items via pattern")
                        return found
                        
                except Exception as e:
                    print(f"[WALL] URL failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"[WALL] Search Error: {e}")
            return None
    
    @staticmethod
    def _extract_data(item):
        """Extract link, title, thumbnail from element"""
        link = None
        title = ""
        thumb = None
        
        if item.name == 'a':
            link = item.get('href', '')
            img = item.find('img')
            if img:
                title = img.get('alt', '')
                thumb = img.get('src') or img.get('data-src')
        
        elif item.name == 'img':
            title = item.get('alt', '') or ''
            thumb = item.get('src') or item.get('data-src')
            parent_a = item.parent
            if parent_a and parent_a.name == 'a':
                link = parent_a.get('href')
            
            # If still no link, look for grandparent
            if not link and parent_a:
                gp = parent_a.parent
                if gp and gp.name == 'a':
                    link = gp.get('href')
        
        else:
            # Generic container (div, article)
            a_tag = item.find('a', href=True)
            if a_tag:
                link = a_tag['href']
            img_tag = item.find('img')
            if img_tag:
                title = img_tag.get('alt', '') or (item.find('h3').get_text() if item.find('h3') else query)
                thumb = img_tag.get('src') or img_tag.get('data-src')
        
        # Clean up URLs
        if thumb and not thumb.startswith(('http', '//')):
            thumb = urljoin("https://hdqwalls.com/", thumb)
        elif thumb and thumb.startswith('//'):
            thumb = 'https:' + thumb
            
        return link, title, thumb
    
    @staticmethod
    def _get_download_page(page_url):
        """Get download links from wallpaper page"""
        info = {'orig': None, 'res': '4K', 'size': '~2MB'}
        
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=8)
            s = BeautifulSoup(r.text, 'html.parser')
            
            # Look for original image
            # Usually in og:image meta tag
            og = s.find('meta', property='og:image')
            if og:
                info['orig'] = og['content']
            
            # Look for download buttons/links
            if not info['orig']:
                # Common patterns on HDQWalls
                dls = s.find_all('a', href=re.compile(r'\.(jpg|png|jpeg)', re.I))
                if dls:
                    href = dls[0].get('href', '')
                    if not href.startswith('http'):
                        href = urljoin(page_url, href)
                    info['orig'] = href
            
            # Resolution extraction
            res_match = re.search(r'(\d{3,4}x\d{3,4})', r.text)
            if res_match:
                info['res'] = res_match.group(1)
                
        except Exception as e:
            print(f"[WALL] Page parse err: {e}")
        
        # Final fallback: if no orig, use page itself (sometimes page is image)
        if not info['orig']:
            info['orig'] = page_url
            
        return info
    
    @staticmethod
    def _fallback_google(query, limit=5):
        """Fallback using DuckDuckGo or direct image search"""
        print("[WALL] Using fallback search...")
        try:
            # Use DuckDuckGo HTML version (no JS needed)
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query + ' wallpaper 4k hdqwalls')}"
            r = requests.get(url, headers={'User-Agent': HEADERS['User-Agent']}, timeout=10)
            s = BeautifulSoup(r.text, 'html.parser')
            
            results = []
            for a in s.find_all('a', class_='result__url')[:limit*2]:
                href = a.get_text(strip=True)
                if 'hdqwalls.com' in href or 'wallpaper' in href.lower():
                    # Extract image from result snippet
                    parent = a.find_parent('div', class_='result')
                    if parent:
                        thumb = parent.find('img', class_='result__icon')
                        thumb_src = thumb.get('src') if thumb else None
                        
                        title = parent.find('h2', class_='result__title')
                        title_txt = title.get_text() if title else query
                        
                        dl_info = WallScraper._get_download_page(href) if 'hdqwalls' in href else {
                            'orig': href.replace('/wallpaper/', '/download/') if 'hdqwalls' in href else href,
                            'res': 'Unknown'
                        }
                        
                        results.append({
                            'title': title_txt[:60],
                            'page': href,
                            'preview': thumb_src,
                            **dl_info
                        })
                        
                        if len(results) >= limit:
                            break
            
            return results if results else None
            
        except Exception as e:
            print(f"[WALL] Fallback failed: {e}")
            return None
    
    @staticmethod
    def optimize(img_path):
        """Compress for mobile"""
        try:
            img = Image.open(img_path).convert('RGB')
            max_s = 1920
            if max(img.size) > max_s:
                ratio = max_s / max(img.size)
                img = img.resize((int(img.size[0]*ratio), int(img.size[1]*ratio)), Image.LANCZOS)
            
            out = io.BytesIO()
            q = 85
            while True:
                out.seek(0); out.truncate()
                img.save(out, 'JPEG', quality=q, optimize=True)
                if len(out.getvalue())/(1024*1024) <= 4 or q <= 50: break
                q -= 10
            out.seek(0)
            return out, f"{img.size[0]}x{img.size[1]}"
        except Exception as e:
            return None, str(e)

sessions = {}

@Client.on_message(filters.command(["wall","4k"]) & filters.private)
async def wall_cmd(c, m):
    try:
        q = m.text.split(None, 1)[1].strip()
    except:
        q = ""
    
    if not q:
        await m.reply("**🖼️ Wallpaper Bot**\n\nUsage:\n`/wall batman`\n`/4k iron man`\n`/wall nature 4k`", parse_mode='md')
        return
    
    wait = await m.reply(f"🔍 Searching **{q}**...")
    
    scr = WallScraper()
    res = scr.find_wallpapers(q, 5)
    
    if not res:
        await wait.edit_text(
            f"❌ **Not Found:** `{q}`\n\n"
            f"Try:\n• Different keywords\n• English names only\n• Shorter queries",
            parse_mode='md'
        )
        return
    
    uid = m.from_user.id
    sessions[uid] = {'r': res, 'i': 0}
    
    await show_result(c, wait, uid, 0)

async def show_result(c, msg, uid, idx):
    ses = sessions[uid]
    r = ses['r']
    idx = max(0, min(idx, len(r)-1))
    ses['i'] = idx
    
    d = r[idx]
    
    txt = (
        f"**🖼️ {d['title']}**\n\n"
        f"📐 Resolution: `{d.get('res','N/A')}`\n"
        f"📦 Size: `{d.get('size','~2MB')}`\n\n"
        f"_Choose option 👇_"
    )
    
    btns = [
        [
            InlineKeyboardButton("◀ Prev", callback_data=f"w_{idx-1}"),
            InlineKeyboardButton(f"{idx+1}/{len(r)}", callback_data="wi"),
            InlineKeyboardButton("Next ▶", callback_data=f"w_{idx+1}")
        ],
        [
            InlineKeyboardButton("⚡ Mobile (Fast)", callback_data=f"wm_{idx}"),
            InlineKeyboardButton("📥 Original (4K)", callback_data=f"wo_{idx}")
        ]
    ]
    
    try:
        preview = d.get('preview') or d.get('orig')
        if hasattr(msg, 'edit_text') and hasattr(msg, 'reply_photo'):
            await msg.delete()
            await c.send_photo(m.chat.id, preview, caption=txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode='md')
        else:
            await c.send_photo(m.chat.id, preview, caption=txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode='md')
    except Exception as e:
        await msg.edit_text(txt + f"\n\n[Preview Link]({d.get('page','#')})", 
                          reply_markup=InlineKeyboardMarkup(btns), disable_web_page_preview=True, parse_mode='md')

@Client.on_callback_query(re.compile("^w"))
async def cb(c, q):
    uid = q.from_user.id
    if uid not in sessions:
        await q.answer("Expired! Search again.", show_alert=True); return
    
    d = q.data.split('_')
    t = d[0]
    i = int(d[1]) if len(d)>1 and d[1] else sessions[uid]['i']
    
    if t == 'wi':
        await q.answer("Info", show_alert=False); return
    
    if len(t) > 1:  # wm_ or wo_
        mode = 'mobile' if 'm' in t else 'original'
        await dl_send(c, q, i, mode)
    else:  # Navigation w_N
        new_i = i
        if '-' in q.data: new_i -= 1
        elif '+' in q.data: new_i += 1
        
        total = len(sessions[uid]['r'])
        if new_i < 0: new_i = total-1
        if new_i >= total: new_i = 0
        
        await q.answer()
        await show_result(c, q.message, uid, new_i)

async def dl_send(c, cb, idx, mode="mobile"):
    ses = sessions[cb.from_user.id]
    d = ses['r'][idx]
    st = await cb.message.reply_text("⏳ Downloading...")
    
    try:
        url = d.get('orig') or d.get('page')
        
        fp = f"{TEMP}/wp_{cb.from_user.id}_{idx}.jpg"
        
        # Download with proper stream
        r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        r.raise_for_status()
        
        with open(fp,'wb') as f:
            for ch in r.iter_content(chunk_size=8192):
                f.write(ch)
        
        sz = os.path.getsize(fp)/(1024*1024)
        
        if mode == 'mobile':
            opt, dims = WallScraper.optimize(fp)
            nm = f"{d['title'][:25]}_mob.jpg".replace('/','_')
            c.send_document(cb.message.chat.id, opt, file_name=nm, 
                          caption=f"⚡ Optimized ({dims})\n🖼️ {d['title']}", force_document=False)
        else:
            nm = f"{d['title'][:25]}_4K.jpg".replace('/','_')
            c.send_document(cb.message.chat.id, fp, file_name=nm, 
                          caption=f"📥 Original ({sz:.1f}MB)\n📐 {d.get('res','4K')}")
        
        if os.path.exists(fp): os.remove(fp)
        await st.delete()
        
    except Exception as e:
        await st.edit_text(f"❌ Failed: {str(e)[:100]}\n\nLink: `{d.get('page','N/A')}`", parse_mode='md')

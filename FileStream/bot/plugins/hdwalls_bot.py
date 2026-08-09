"""
HDQWalls Plugin - Compact Version
Command: /wall <query>
"""

import os, re, io, time
from pathlib import Path
from urllib.parse import urljoin, quote_plus as qplus
import requests
from bs4 import BeautifulSoup
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

TMP = Path("temp_hdw"); TMP.mkdir(exist_ok=True)
H = {"User-Agent":"Mozilla/5.0","Referer":"https://hdqwalls.com/"}
BASE = "https://hdqwalls.com"
S = {}  # Sessions: {uid: {results, idx, query}}

def get(url):
    try:
        r = requests.get(url, headers=H, timeout=15)
        return BeautifulSoup(r.text,'html.parser') if r.status_code==200 else None
    except: return None

def dl(url,p=None):
    if not p: p=str(TMP/f"{time.time()}.jpg")
    try:
        r=requests.get(url,**{**H,"stream":True},timeout=30)
        if r.status==200:
            open(p,'wb').write(r.content)
            return p if os.path.getsize(p)>10000 else None
    except: pass
    return None

async def send_img(c,uid,path,cap,btns):
    await c.send_photo(uid,photo=open(path,'rb'),caption=cap,
                       reply_markup=InlineKeyboardMarkup(btns),parse_mode='md')
    try: os.remove(path)
    except: pass

@Client.on_message(filters.command(["ll"])&filters.private)
async def wall(c,m):
    try: q=m.text.split(None,1)[1].strip()
    except IndexError: q=""
    
    if not q:
        await m.reply("**Usage:** `/wall batman`\n`/wall iron man`",parse_mode='md');return
    
    st=await m.reply(f"⏳ Searching `{q}`...")
    
    items=[]
    soup=get(f"{BASE}/wallpapers/{qplus(q)}")
    if soup:
        # Find all articles or figures containing wallpaper links
        arts=soup.find_all('article') or soup.find_all('figure') or \
             [a for a in soup.find_all('a',href=re.compile('/wallpaper/')) if a.find('img')]
        
        seen=set()
        for a in arts[:12]:
            try:
                # Extract link
                link=a['href'] if a.name=='a' else (a.find('a')['href'] if a.find('a') else None)
                if not link or link in seen: continue
                seen.add(link)
                
                img=a.find('img') if a.name!='img' else a
                if not img: continue
                
                title=img.get('alt','') or 'Wallpaper'
                thumb=img.get('src','') or img.get('data-src','')
                page=urljoin(BASE,link)
                
                # Visit page to get download URL
                pg=get(page)
                orig=""
                res="HD"
                sz="~2MB"
                
                if pg:
                    og=pg.find('meta',property='og:image')
                    if og: orig=og['content']
                    
                    # Find download buttons
                    for btn in pg.find_all(['a','button'],string=re.compile('download|Download')):
                        btxt=btn.get_text().lower()
                        href=urljoin(page,btn.get('href',''))
                        if ('original' in btxt or '4k' in btxt) or (not orig):
                            orig=href
                        if any(x in btxt for x in ['1080','2400','mobile']):
                            pass  # Mobile variant
                    
                    # Resolution text extraction
                    txt=' '.join([x for x in pg.strings])
                    rm=re.search(r'(\d{3,4}\s*x\s*\d{3,4})',txt,re.I)
                    sm=re.search(r'(\d+\.?\d*\s*MB)',txt,re.I)
                    if rm: res=rm.group(1).replace(' ','')
                    if sm: sz=sm.group(1)
                
                if orig:
                    items.append({
                        't':title,'page':page,'thumb':urljoin(BASE,thumb) if thumb else '',
                        'orig':orig,'res':res,'sz':sz
                    })
                    
                if len(items)>=6: break
            except: continue
    
    S[m.from_user.id]={'r':items,'i':0,'q':q}
    
    if not items:
        await st.edit_text(f"❌ No results for `{q}`\nTry: `batman`, `nature`, `cyberpunk`",parse_mode='md')
        return
    
    await show(c,m.from_user.id,0)

async def show(c,uid,i):
    d=S[uid];lst=d['r']
    i=max(0,min(i,len(lst)-1));d['i']=i
    it=lst[i]
    
    ld=await c.send_message(uid,"⏳ Loading...")
    
    pth=dl(it['thumb'] or it['orig'])
    if not pth:
        await ld.edit_text("❌ Load failed");return
    
    cap=(f"**{it['t']}**\n\n"
         f"📐 `{it['res']}` | 📦 `{it['sz']}`")
    
    n=len(lst)
    b=[
        [
            InlineKeyboardButton("◀",callback_data=f"h:{uid}:{max(0,i-1)}"),
            InlineKeyboardButton(f"{i+1}/{n}",callback_data="hx"),
            InlineKeyboardButton("▶",callback_data=f"h:{uid}:{min(i+1,n-1)}")
        ],
        [
            InlineKeyboardButton("⚡ Mobile",callback_data=f"hm:{uid}:{i}"),
            InlineKeyboardButton("📥 Original",callback_data=f"ho:{uid}:{i}")
        ]
    ]
    
    await send_img(c,uid,pth,cap,b)
    try: 
        await ld.delete()
        # Delete previous status if exists
    except: pass

@Client.on_callback_query(re.compile("^h"))
async def cb(c,q):
    d=q.data.split(':')
    act=d[1]
    uid=int(d[2]);idx=int(d[3]) if len(d)>3 else 0
    s=S.get(uid)
    if not s: await q.answer("Expired");return
    await q.answer()
    
    if act=='m': # Mobile
        it=s['r'][idx];st=await c.send_message(uid,"⏳ Compressing...")
        p=dl(it['orig'])
        if p:
            im=Image.open(p).convert('RGB')
            im.thumbnail((1920,1920),Image.LANCZOS)
            buf=io.BytesIO()
            im.save(buf,"JPEG",quality=85,optimize=True);buf.seek(0)
            fn=it['t'][:20].replace('/','_')+".jpg"
            await c.send_document(uid,buf,file_name=fn,caption="✅ Mobile ready",force_document=False)
            os.remove(p);await st.delete()
    elif act=='o': # Original
        it=s['r'][idx];st=await c.send_message(uid,"⏳ Downloading full...")
        p=dl(it['orig'])
        if p:
            sz=os.path.getsize(p)/1024/1024
            if sz<45:
                await c.send_document(uid,p,file_name=it['t'][:25].replace('/','_')+".jpg",
                                      caption=f"📥 {it['res']} | {sz:.1f}MB")
            else:
                await st.edit_text(f"⚠️ Too large ({sz:.1f}MB)\nLink:`{it['orig']}`",parse_mode='md');return
            os.remove(p);await st.delete()
    else:
        await show(c,uid,idx)

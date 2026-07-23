import os,re,time,uuid,asyncio,aiohttp
from pyrogram import Client,filters,StopPropagation
from pyrogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton

TMDB_API = os.getenv("TMDB_API","18303910643c603ebb9e370f2f49db56")
FANART_KEY = os.getenv("FANART_API","")
CACHE={}; TTL=3600; PAGE=20

def cb(s): return filters.create(lambda f,c,q:q.data.startswith(s))
def clean(): [CACHE.pop(k) for k in list(CACHE.keys()) if time.time()-CACHE[k].get('t',0)>TTL]
def token(c): return os.getenv("BOT_TOKEN") or c.bot_token or _("No Token")
def _(p): return f"https://image.tmdb.org/t/p/original{p}" if p else None
def uniq(l): return list(dict.fromkeys(l))
def tit(m): return m.get("title") or m.get("name") or m.get("original_title") or "Unknown"
def yr(m): d=m.get("release_date") or m.get("first_air_date"); return d[:4] if len(d)>=4 else "N/A"
def cn(cat): 
    return {"posters_en":"🇬🇧 English","posters_hi":"🇮🇳 Hindi","posters_all":"🖼️ Portrait",
            "landscape":"🎬 Best Keyarts","wide":"🌅 More Promos","backdrops":"📸 Screenshots",
            "clearart":"✨ ClearArt","discs":"💿 Discs","logos":"🔤 Logos"}.get(cat,cat)

# API Calls
async def search(q):
    async with aiohttp.ClientSession() as s:
        r=await s.get(f"https://api.themoviedb.org/3/search/multi",params={"api_key":TMDB_API,"query":q})
        return await r.json()

async def imgs(typ,id):
    async with aiohttp.ClientSession() as s:
        r=await s.get(f"https://api.themoviedb.org/3/{typ}/{id}/images",params={"api_key":TMDB_API,"include_image_language":"en,hi,null"})
        return await r.json()

async def fan(id,t="movies"):
    if not FANART_KEY: return {}
    try:
        async with aiohttp.ClientSession() as s:
            r=await s.get(f"https://webservice.fanart.tv/v3/{t}/{id}",params={"api_key":FANART_KEY},timeout=5)
            return await r.json() if r.status==200 else {}
    except: return {}

# Smart Classifier - Ye wala function tumhara main hai!
def classify(mv,d,fd=None):
    pts=sorted(d.get("posts",[])or[],key=lambda x:(x.get("vote_av",0),x.get("vote_ct",0)),reverse=True)
    bds=sorted(d.get("backdrops",[])or[],key=lambda x:(x.get("vote_av",0),x.get("vote_ct",0)),reverse=True)
    lgs=sorted(d.get("logos",[])or[],key=lambda x:(x.get("vote_av",0),x.get("vote_ct",0)),reverse=True)
    
    cat={"logos":[],"pe":[],"ph":[],"pa":[],"land":[],"wid":[],"bds":[],"ca":[],"dc":[]}
    
    # Posters
    if mv.get("poster_path"): cat["pa"].insert(0,_(mv["poster_path"]))
    for i in pts:
        u=_(i.get("file_path")); l=i.get("iso_639_1")
        if u: cat["pa"].append(u); 
        if l=="en" and u: cat["pe"].append(u)
        elif l=="hi" and u: cat["ph"].append(u)
    
    # Backdrops Separation Logic
    p=[]; s=[]
    if mv.get("backdrop_path"): p.append(_(mv["backdrop_path"]))
    
    for i in bds:
        u=_(i.get("file_path"))
        if not u or u in p: continue
        w=i.get("width",0); h=i.get("height",0); v=i.get("vote_count",0); a=i.get("vote_average",0)
        ar=w/max(h,1)
        
        # Premium Art vs Screenshot check
        is_promo=(v>=3 and a>=5) or(w>=1920 and 1.7<=ar<=2.4 and not((w,h)in[(1920,1080),(3840,2160),(1280,720)])) or(a>=7 and w>=1280)
        
        (p if is_promo else s).append(u)
    
    cat["land"]=uniq(p[:15]); cat["wid"]=uniq(p[15:]) if len(p)>15 else []
    cat["bds"]=uniq(s)
    
    # Logos
    for i in lgs:
        u=_(i.get("file_path"))
        if u: cat["logos"].append(u)
    
    # Fanart extras
    if fd:
        for item in (fd.get("hdmovieclearart")or[])[:8]:
            u=item.get("url")
            if u: cat["ca"].append(u)
        for item in (fd.get("moviedisc")or[])[:5]:
            u=item.get("url")
            if u: cat["dc"].append(u)
    
    return {k:uniq(v) for k,v in cat.items() if v}

# Buttons
def mk_btns(t,cats):
    b=[]
    r=[i for x in [("posters_en","🇬🇧 EN","pe"),("posters_hi","🇮🇳 HI","ph")] for i in[InlineKeyboardButton(f"{x[1]} ({len(cats[x[2]])})",data=f"ic|{t}|{x[2]}")] if cats.get(x[2])]
    if r: b.append(r)
    if cats.get("pa"): b.append([InlineKeyboardButton(f"🖼️ Portrait ({len(cats['pa'])})",data=f"ic|{t}|pa")])
    
    lr=[]
    if cats.get("land"): lr.append(InlineKeyboardButton(f"🎬 Keyarts ({len(cats['land'])})",data=f"ic|{t}|land"))
    if cats.get("wid"): lr.append(InlineKeyboardButton(f"🌅 More ({len(cats['wid'])})",data=f"ic|{t}|wid"))
    if lr: b.append(lr)
    
    fr=[]
    if cats.get("ca"): fr.append(InlineKeyboardButton(f"✨ ClearArt ({len(cats['ca'])})",data=f"ic|{t}|ca"))
    if cats.get("dc"): fr.append(InlineKeyboardButton(f"💿 Discs ({len(cats['dc'])})",data=f"ic|{t}|dc"))
    if fr: b.append(fr)
    if cats.get("bds"): b.append([InlineKeyboardButton(f"📸 Screenshots ({len(cats['bds'])})",data=f"ic|{t}|bds")])
    if len(cats.get("logs",[]))>2: b.append([InlineKeyboardButton(f"🔤 Logos ({len(cats['logos'])})",data=f"ic|{t}|logs")])
    b.append([InlineKeyboardButton("❌ Cancel",data=f"ix|{t}")])
    return InlineKeyboardMarkup(b)

def pg_btn(t,cat,p,total):
    tp=max(1,(total+PAGE-1)//PAGE); st=p*PAGE+1; ed=min(st+PAGE-1,total); cnt=ed-st+1
    b=[[InlineKeyboardButton(f"📤 Send {st}-{ed} ({cnt}) ",data=f"is|{t}|{cat}|{p}")]]
    nb=[]
    if p>0: nb.append(InlineKeyboardButton("⬅️ Prev",data=f"ip|{t}|{cat}|{p-1}"))
    if tp>1: nb.append(InlineKeyboardButton(f"{p+1}/{tp}",data="-"))
    if p<tp-1: nb.append(InlineKeyboardButton("Next ➡️",data=f"ip|{t}|{cat}|{p+1}"))
    if nb: b.append(nb)
    b.append([InlineKeyboardButton("🔙 Back",data=f"ib|{t}"),InlineKeyboardButton("❌ Cancel",data=f"ix|{t}")])
    return InlineKeyboardMarkup(b)

def pg_txt(mv,cat,p,total):
    return f"**{tit(mv)}** ({yr(mv)})\n📁 **{cn(cat)}**\n🖼 Total:**{total}**\n\n📄 Page**{p+1}**"

# Send Function - 20 pics at once (10+10 albums)
async def send20(c,chat,imgs,rt=None,tid=None):
    tk=token(c); ok=0; fail=0
    async with aiohttp.ClientSession() as s:
        for bn,i in enumerate(range(0,len(imgs),10),1):
            ch=imgs[i:i+10]
            try:
                if len(ch)==1:
                    api=f"https://api.telegram.org/bot{tk}/sendPhoto"
                    payload={"chat_id":chat,"photo":ch[0],"allow_sending_without_reply":True}
                else:
                    api=f"https://api.telegram.org/bot{tk}/sendMediaGroup"
                    payload={"chat_id":chat,"media":[{"type":"photo","media":u}for u in ch],"allow_sending_without_reply":True}
                if rt:payload["reply_to_message_id"]=rt
                if tid:payload["message_thread_id"]=tid
                
                r=await s.post(api,json=payload)
                res=await r.json()
                ok+=len(ch)if res.get("ok")else 0
                fail+=len(ch)if not res.get("ok")else 0
                if i+10<len(imgs): await asyncio.sleep(0.8)
            except: fail+=len(ch)
    return ok,fail

# Handlers
@Client.on_message(filters.command("img")&(filters.private|filters.group))
async def imgcmd(c,m):
    clean()
    if len(m.command)<2: return await m.reply("`/img movie year`")
    q=" ".join(m.command[1:]).strip(); st=await m.reply("🔍 Searching...")
    try:
        y=re.search(r'\b(19|20)\d{2}\b',q); yr_=y.group() if y else None
        nm=re.sub(r'\b(19|20)\d{2}\b','',q).strip() or q
        sr=await search(nm); res=sr.get("results",[]); mv=None
        
        for x in res:
            if x.get("media_type")in["movie","tv"]:
                if yr_:
                    d=x.get("release_date")or x.get("first_air_date")
                    if d and d.startswith(yr_): mv=x;break
                elif not mv: mv=x
        
        if not mv: return await st.edit_text("❌ Not found!")
        typ=mv.get("media_type","movie"); mid=mv["id"]
        await st.edit_text(f"🖼️ Fetching **{tit(mv)}**...")
        di=await imgs(typ,mid); fi=await fan(mid,"movies"if typ=="movie"else"tv")
        cls=classify(mv,di,fi)
        
        if not cls: return await st.edit_text("⚠️ No images!")
        t=uuid.uuid4().hex[:10]
        CACHE[t]={"uid":m.from_user.id,"cid":m.chat.id,"rt":m.id,"tid":getattr(m,'message_thread_id',None),"mv":mv,"c":cls,"t":time.time()}
        await st.edit_text(f"🎬 **{tit(mv)}** ({yr(mv)})\n_Select:",reply_markup=mk_btns(t,cls))
    except Exception as e: await st.edit_text(f"`{e}`")

@Client.on_callback_query(cb("ic|"),group=-999)
async def icat(c,q):
    try:
        _,t,cat=q.data.split("|");d=CACHE[t]
        if not d or q.from_user.id!=d["uid"]: return q.answer("Exp!",show_alert=True)
        im=d["c"].get(cat,[])
        if not im: return q.answer("Empty!",show_alert=True)
        await q.message.edit_text(pg_txt(d["mv"],cat,0,len(im)),reply_markup=pg_btn(t,cat,0,len(im))); q.answer(cn(cat))
    finally: raise StopPropagation

@Client.on_callback_query(cb("ip|"),group=-999)
async def ipage(c,q):
    try:
        _,t,cat,p=q.data.split("|");p=int(p);d=CACHE[t]
        if not d or q.from_user.id!=d["uid"]: return q.answer("!",show_alert=True)
        im=d["c"].get(cat,[]);tl=len(im);tp=max(1,(tl+PAGE-1)//PAGE);p=max(0,min(p,tp-1))
        await q.message.edit_text(pg_txt(d["mv"],cat,p,tl),reply_markup=pg_btn(t,cat,p,tl)); q.answer(f"P{p+1}")
    finally: raise StopPropagation

@Client.on_callback_query(cb("is|"),group=-999)
async def isend(c,q):
    try:
        _,t,cat,p=q.data.split("|");p=int(p);d=CACHE[t]
        if not d or q.from_user.id!=d["uid"]: return q.answer("!",show_alert=True)
        im=d["c"].get(cat,[]);st=p*PAGE;ed=min(st+PAGE,len(im));sel=im[st:ed]
        if not sel: return q.answer("Empty range!",show_alert=True)
        q.answer(f"Sending {len(sel)}..."); await q.message.edit_text("⬆️ Uploading...")
        ok,fail=await send20(c,q.message.chat.id,sel,d.get("rt"),d.get("tid"))
        await q.message.edit_text(f"✅ Sent **{ok}** images!\n_Albums: {(ok//10)+(1 if ok%10>0 else 0)}_\n_Next/Prev for more_",reply_markup=pg_btn(t,cat,p,len(im)))
    except Exception as e: await q.message.edit_text(f"`{e}`")
    finally: raise StopPropagation

@Client.on_callback_query(cb("ib|"),group=-999)
async def iback(c,q):
    try:
        _,t=q.data.split("|");d=CACHE[t]
        if not d or q.from_user.id!=d["uid"]: return q.answer("!",show_alert=True)
        await q.message.edit_text(f"🎬 **{tit(d['mv'])}** ({yr(d['mv'])}\n_Select:",reply_markup=mk_btns(t,d["c"])); q.answer("Back")
    finally: raise StopPropagation

@Client.on_callback_query(cb("ix|"),group=-999)
async def ixcl(c,q):
    try:
        _,t=q.data.split("|");d=CACHE.get(t)
        if d and q.from_user.id!=d.get("uid"): return q.answer("!",show_alert=True)
        CACHE.pop(t,None); q.answer("Cancel"); q.message.edit_text("❌ Cancelled.")
    finally: raise StopPropagation

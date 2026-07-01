import aiohttp

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from FileStream.bot import FileStream


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@FileStream.on_message(filters.command("img"))
async def img(_, m):

    if len(m.command) < 2:
        return await m.reply_text("Use: /img movie name")

    query = " ".join(m.command[1:])

    msg = await m.reply_text("🔎 Searching...")


    async with aiohttp.ClientSession() as s:

        url = (
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_API}&query={query}"
        )

        async with s.get(url) as r:
            data = await r.json()


    btn=[]

    for x in data.get("results", [])[:8]:

        if x.get("media_type") not in ["movie","tv"]:
            continue

        title = x.get("title") or x.get("name")

        btn.append(
        [
        InlineKeyboardButton(
            title,
            callback_data=f"poster_{x['id']}_{x['media_type']}"
        )
        ])


    if not btn:
        return await msg.edit("❌ No Result Found")


    await msg.edit(
        "🎬 Select:",
        reply_markup=InlineKeyboardMarkup(btn)
    )



@FileStream.on_callback_query(filters.regex("^poster_"))
async def poster(_, q):

    try:

        _, mid, typ = q.data.split("_")


        async with aiohttp.ClientSession() as s:

            url = (
            f"https://api.themoviedb.org/3/{typ}/{mid}/images"
            f"?api_key={TMDB_API}"
            )

            async with s.get(url) as r:
                data = await r.json()


        btn=[]


        for i,p in enumerate(data.get("posters",[])[:10],1):

            link = (
            "https://image.tmdb.org/t/p/original"
            +
            p["file_path"]
            )


            btn.append(
            [
            InlineKeyboardButton(
                f"{i}. Click Here",
                url=link
            )
            ])


        await q.message.edit(
            "📦 **Available Posters**\n\n👇 Choose:",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    except Exception as e:
        await q.answer(
            "Poster error",
            show_alert=True
        )

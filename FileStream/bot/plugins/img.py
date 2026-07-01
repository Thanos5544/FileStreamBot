import aiohttp

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)

from FileStream.bot import FileStream


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@FileStream.on_message(filters.command("img"))
async def img(_, m):

    if len(m.command) < 2:
        return await m.reply_text(
            "❌ Use:\n/img movie name"
        )

    query = " ".join(m.command[1:])

    msg = await m.reply_text(
        "🔎 Searching..."
    )


    async with aiohttp.ClientSession() as s:

        url = (
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_API}&query={query}"
        )

        async with s.get(url) as r:
            data = await r.json()


    buttons = []

    for x in data.get("results", [])[:10]:

        if x.get("media_type") not in ["movie", "tv"]:
            continue

        title = x.get("title") or x.get("name")

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎬 {title}",
                    callback_data=f"poster#{x['id']}#{x['media_type']}"
                )
            ]
        )


    if not buttons:
        return await msg.edit(
            "❌ No Result Found"
        )


    await msg.edit(
        "👇 Select Movie / Series",
        reply_markup=InlineKeyboardMarkup(buttons)
    )



@FileStream.on_callback_query(filters.regex("^poster#"))
async def poster(_, q):

    await q.answer("Fetching HD Images...")


    _, mid, typ = q.data.split("#")


    async with aiohttp.ClientSession() as s:

        url = (
            f"https://api.themoviedb.org/3/{typ}/{mid}/images"
            f"?api_key={TMDB_API}"
        )

        async with s.get(url) as r:
            data = await r.json()



    pics = []


    for p in data.get("backdrops", [])[:15]:

        pics.append(
            "https://image.tmdb.org/t/p/original"
            + p["file_path"]
        )


    for p in data.get("posters", [])[:5]:

        pics.append(
            "https://image.tmdb.org/t/p/original"
            + p["file_path"]
        )


    pics = pics[:20]


    if not pics:
        return await q.message.reply_text(
            "❌ Images not found"
        )


    media = []

    for img in pics:

        media.append(
            InputMediaPhoto(img)
        )


    await q.message.delete()

    await q.message.reply_media_group(media)

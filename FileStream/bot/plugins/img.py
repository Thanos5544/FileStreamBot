import aiohttp

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from FileStream.bot import FileStream


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@FileStream.on_message(filters.command("img"))
async def search_movie(_, m):

    if len(m.command) < 2:
        return await m.reply_text(
            "❌ Use:\n/img movie name"
        )

    name = " ".join(m.command[1:])

    msg = await m.reply_text(
        "🔎 Searching..."
    )


    async with aiohttp.ClientSession() as s:

        url = (
        "https://api.themoviedb.org/3/search/multi"
        f"?api_key={TMDB_API}&query={name}"
        )

        async with s.get(url) as r:
            data = await r.json()


    buttons=[]


    for item in data.get("results", [])[:10]:

        title = (
        item.get("title")
        or
        item.get("name")
        )


        media = item.get("media_type")


        if media not in ["movie","tv"]:
            continue


        buttons.append(
        [
        InlineKeyboardButton(
            title,
            callback_data=f"poster#{item['id']}#{media}"
        )
        ])


    if not buttons:
        return await msg.edit(
            "❌ No Result Found"
        )


    await msg.edit(
        "🎬 **Select Movie / Series**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )





@FileStream.on_callback_query(filters.regex("^poster#"))
async def poster(_, q):

    _, movie_id, typ = q.data.split("#")


    async with aiohttp.ClientSession() as s:

        url = (
        f"https://api.themoviedb.org/3/{typ}/{movie_id}/images"
        f"?api_key={TMDB_API}"
        )

        async with s.get(url) as r:
            data = await r.json()


    buttons=[]


    for i, poster in enumerate(
        data.get("posters",[])[:10],
        1
    ):

        link = (
        "https://image.tmdb.org/t/p/original"
        +
        poster["file_path"]
        )


        buttons.append(
        [
        InlineKeyboardButton(
            f"{i}. Click Here",
            url=link
        )
        ])



    if not buttons:
        return await q.answer(
            "❌ Poster not found",
            show_alert=True
        )


    await q.message.edit(
        "📦 **Available Posters**\n\n"
        "🖼 **Posters:**\n\n"
        "👇 Choose Poster",
        reply_markup=InlineKeyboardMarkup(buttons)
        )

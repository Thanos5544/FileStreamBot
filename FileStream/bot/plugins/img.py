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
async def img_search(_, m):

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


    buttons = []

    for x in data.get("results", [])[:8]:

        if x.get("media_type") not in ["movie", "tv"]:
            continue

        title = x.get("title") or x.get("name")

        buttons.append(
            [
                InlineKeyboardButton(
                    title,
                    callback_data=f"img_{x['id']}_{x['media_type']}"
                )
            ]
        )


    if not buttons:
        return await msg.edit(
            "❌ No Result Found"
        )


    await msg.edit(
        "🎬 Select Movie / Series",
        reply_markup=InlineKeyboardMarkup(buttons)
    )




@FileStream.on_callback_query(filters.regex("^img_"))
async def send_images(_, q):

    _, mid, typ = q.data.split("_")


    await q.answer("Fetching HD Images...")


    async with aiohttp.ClientSession() as s:

        url = (
            f"https://api.themoviedb.org/3/{typ}/{mid}/images"
            f"?api_key={TMDB_API}"
        )

        async with s.get(url) as r:
            data = await s.json()



    photos = []


    # backdrops
    for x in data.get("backdrops", [])[:15]:

        photos.append(
            InputMediaPhoto(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )
        )


    # posters
    for x in data.get("posters", [])[:5]:

        photos.append(
            InputMediaPhoto(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )
        )


    if not photos:
        return await q.message.reply_text(
            "❌ Images not found"
        )


    await q.message.delete()


    await q.message.reply_media_group(
        photos[:20]
    )

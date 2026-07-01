import aiohttp

from pyrogram import filters
from pyrogram.types import InputMediaPhoto

from pyrogram import Client

from plugins.Dreamxfutures.Imdbposter import get_movie_detailsx


@Client.on_message(filters.command("img"))
async def img(_, m):

    if len(m.command) < 2:
        return await m.reply_text(
            "❌ Use:\n/img movie name"
        )

    name = " ".join(m.command[1:])


    msg = await m.reply_text(
        "🔎 Fetching HD Images..."
    )


    data = await get_movie_detailsx(name)


    if not data:
        return await msg.edit(
            "❌ Movie not found"
        )


    pics = []


    if data.get("poster_url"):
        pics.append(data["poster_url"])

    if data.get("backdrop_url"):
        pics.append(data["backdrop_url"])


    # TMDB images
    tmdb_id = data.get("id")
    media = data.get("type", "movie")


    if tmdb_id:

        async with aiohttp.ClientSession() as s:

            url = (
            f"https://api.themoviedb.org/3/{media}/{tmdb_id}/images"
            f"?api_key=18303910643c603ebb9e370f2f49db56"
            )

            async with s.get(url) as r:
                img = await r.json()


        for p in img.get("backdrops", [])[:18]:

            pics.append(
            "https://image.tmdb.org/t/p/original"
            + p["file_path"]
            )


    pics = list(dict.fromkeys(pics))[:20]


    if not pics:
        return await msg.edit(
            "❌ Images not found"
        )


    media=[]

    for x in pics:
        media.append(
            InputMediaPhoto(x)
        )


    await m.reply_media_group(
        media
    )


    await msg.delete()

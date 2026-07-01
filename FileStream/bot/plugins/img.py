from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio


TMDB_API = "18303910643c603ebb9e370f2f49db56"
IMG = "https://image.tmdb.org/t/p/original"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name year"
        )

    name = " ".join(message.command[1:])

    msg = await message.reply_text(
        "🔎 Fetching HD Images..."
    )

    try:

        async with aiohttp.ClientSession() as session:

            # search with year support
            search_url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}&include_adult=false"
            )

            async with session.get(search_url) as r:
                search = await r.json()


            if not search.get("results"):
                return await msg.edit("❌ Not Found")


            result = search["results"][0]

            media_type = result.get("media_type")

            if media_type not in ["movie", "tv"]:
                media_type = "movie"


            mid = result["id"]


            img_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{mid}/images"
                f"?api_key={TMDB_API}"
            )


            async with session.get(img_url) as r:
                images_data = await r.json()



        pics = []


        # main poster
        if result.get("poster_path"):
            pics.append(
                IMG + result["poster_path"]
            )


        # main backdrop
        if result.get("backdrop_path"):
            pics.append(
                IMG + result["backdrop_path"]
            )


        # all posters
        for p in images_data.get("posters", []):
            pics.append(
                IMG + p["file_path"]
            )


        # all backdrops
        for b in images_data.get("backdrops", []):
            pics.append(
                IMG + b["file_path"]
            )


        # remove duplicate
        pics = list(dict.fromkeys(pics))[:20]


        if not pics:
            return await msg.edit(
                "❌ Images not found"
            )


        await msg.edit(
            "⬆️ Uᴘʟᴏᴀᴅɪɴɢ 20 ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        for i in range(0, len(pics), 10):

            album = []

            for pic in pics[i:i+10]:
                album.append(
                    InputMediaPhoto(pic)
                )


            await message.reply_media_group(
                album
            )


            await asyncio.sleep(3)


        await message.reply_text(
            "🖼️ Source: @Patrick_Botz"
        )


        await msg.delete()


    except Exception as e:

        await msg.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

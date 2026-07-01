from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio
import re


TMDB_API = "18303910643c603ebb9e370f2f49db56"
IMG = "https://image.tmdb.org/t/p/original"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name year"
        )


    query = " ".join(message.command[1:])


    year = None
    m = re.search(r"(19|20)\d{2}", query)

    if m:
        year = m.group()
        query = query.replace(year, "").strip()


    msg = await message.reply_text(
        "🔎 Fetching HD Images..."
    )


    try:

        async with aiohttp.ClientSession() as session:


            search_url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}"
                f"&query={query}"
                "&include_adult=false"
            )


            async with session.get(search_url) as r:
                search = await r.json()


            results = search.get("results", [])


            if year:

                results = [
                    x for x in results
                    if year in (
                        x.get("release_date","")
                        or
                        x.get("first_air_date","")
                    )
                ]


            if not results:
                return await msg.edit("❌ Not Found")


            item = results[0]


            media_type = item.get(
                "media_type",
                "movie"
            )

            mid = item["id"]



            image_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{mid}/images"
                f"?api_key={TMDB_API}"
                "&include_image_language=en,null"
            )


            async with session.get(image_url) as r:
                data = await r.json()



        photos = []


        # Poster
        if item.get("poster_path"):

            photos.append(
                IMG + item["poster_path"]
            )


        # Backdrops
        for x in data.get("backdrops", [])[:50]:

            if x.get("file_path"):

                photos.append(
                    IMG + x["file_path"]
                )


        # More posters
        for x in data.get("posters", [])[:10]:

            if x.get("file_path"):

                photos.append(
                    IMG + x["file_path"]
                )


        photos = list(dict.fromkeys(photos))


        if not photos:
            return await msg.edit(
                "❌ Images not found"
            )


        total = min(len(photos),20)


        for i in range(0,total,10):

            album = []


            for p in photos[i:i+10]:

                album.append(
                    InputMediaPhoto(p)
                )


            await message.reply_media_group(
                album
            )


            if i + 10 < total:
                await asyncio.sleep(8)



        await msg.delete()



    except Exception as e:

        await msg.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

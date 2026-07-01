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
            "❌ Use:\n/img movie name"
        )

    name = " ".join(message.command[1:])

    msg = await message.reply_text(
        "🔎 Fetching HD Images..."
    )

    try:

        year = None
        match = re.search(r"(19|20)\d{2}", name)

        if match:
            year = match.group()
            clean_name = name.replace(year, "").strip()
        else:
            clean_name = name


        async with aiohttp.ClientSession() as session:

            search_url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={clean_name}"
            )

            async with session.get(search_url) as resp:
                search = await resp.json()


            results = search.get("results", [])


            if year:
                for r in results:
                    date = r.get("release_date") or r.get("first_air_date")

                    if date and date.startswith(year):
                        results = [r]
                        break


            if not results:
                return await msg.edit("❌ Not found")


            movie = results[0]

            media_type = movie.get(
                "media_type",
                "movie"
            )

            movie_id = movie["id"]


            image_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{movie_id}/images"
                f"?api_key={TMDB_API}"
            )


            async with session.get(image_url) as resp:
                data = await resp.json()



        images = []


        if movie.get("poster_path"):
            images.append(
                IMG + movie["poster_path"]
            )


        for x in data.get("posters", []):

            url = IMG + x["file_path"]

            if url not in images:
                images.append(url)



        for x in data.get("backdrops", []):

            url = IMG + x["file_path"]

            if url not in images:
                images.append(url)



        images = images[:20]


        await msg.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(images)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        # first 10
        for i in range(0, len(images), 10):

            album = []

            for pic in images[i:i+10]:
                album.append(
                    InputMediaPhoto(pic)
                )


            await message.reply_media_group(album)

            await asyncio.sleep(3)


        await msg.delete()


    except Exception as e:
        print("IMG ERROR:", e)

        try:
            await msg.delete()
        except:
            pass

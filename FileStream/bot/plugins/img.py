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
            "❌ Use:\n/img movie name"
        )

    name = " ".join(message.command[1:])

    msg = await message.reply_text(
        "🔎 Fetching HD Images..."
    )

    try:

        async with aiohttp.ClientSession() as session:

            search_url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(search_url) as resp:
                search = await resp.json()


            if not search.get("results"):
                return await msg.edit("❌ Not found")


            movie = search["results"][0]

            media_type = movie.get("media_type", "movie")
            movie_id = movie["id"]


            image_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{movie_id}/images"
                f"?api_key={TMDB_API}"
            )


            async with session.get(image_url) as resp:
                data = await resp.json()


        images = []


        # Poster first
        if movie.get("poster_path"):
            images.append(
                IMG + movie["poster_path"]
            )


        # More posters
        for p in data.get("posters", []):

            url = IMG + p["file_path"]

            if url not in images:
                images.append(url)



        # Backdrops if needed
        for b in data.get("backdrops", []):

            url = IMG + b["file_path"]

            if url not in images:
                images.append(url)


        # ONLY 20
        images = images[:20]


        if not images:
            return await msg.edit("❌ Images not found")


        await msg.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(images)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        # Telegram max 10
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

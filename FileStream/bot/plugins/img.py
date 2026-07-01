import aiohttp
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto


TMDB_API = "18303910643c603ebb9e370f2f49db56"

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/original"


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

        year = None
        match = re.search(r"(19|20)\d{2}", name)

        if match:
            year = match.group()
            search_name = name.replace(year, "").strip()
        else:
            search_name = name


        async with aiohttp.ClientSession() as session:

            search_url = (
                f"{TMDB_BASE}/search/multi"
                f"?api_key={TMDB_API}&query={search_name}"
            )

            async with session.get(search_url) as resp:
                search = await resp.json()


            results = [
                x for x in search.get("results", [])
                if x.get("media_type") in ["movie", "tv"]
            ]


            if not results:
                return await msg.edit("❌ Not found")


            movie = results[0]


            if year:
                for x in results:
                    date = (
                        x.get("release_date")
                        or x.get("first_air_date")
                    )

                    if date and date.startswith(year):
                        movie = x
                        break


            media_type = movie.get("media_type", "movie")
            movie_id = movie["id"]


            image_url = (
                f"{TMDB_BASE}/{media_type}/{movie_id}/images"
                f"?api_key={TMDB_API}"
            )


            async with session.get(image_url) as resp:
                data = await resp.json()



        images = []


        # English / Original posters first
        for x in data.get("posters", []):

            lang = x.get("iso_639_1")

            if lang in [None, "en"]:

                images.append(
                    TMDB_IMG + x["file_path"]
                )


            if len(images) >= 15:
                break



        # Hindi posters after
        for x in data.get("posters", []):

            if x.get("iso_639_1") == "hi":

                images.append(
                    TMDB_IMG + x["file_path"]
                )


            if len(images) >= 18:
                break



        # Backdrops
        for x in data.get("backdrops", []):

            images.append(
                TMDB_IMG + x["file_path"]
            )

            if len(images) >= 20:
                break



        images = list(dict.fromkeys(images))[:20]


        if not images:
            return await msg.edit("❌ No images found")


        await msg.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(images)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        for i in range(0, len(images), 10):

            album = []

            for pic in images[i:i+10]:

                album.append(
                    InputMediaPhoto(media=pic)
                )


            try:

                await client.send_media_group(
                    chat_id=message.chat.id,
                    media=album,
                    reply_to_message_id=message.id
                )

            except Exception as e:
                print("MEDIA ERROR:", e)


            await asyncio.sleep(1)



        await message.reply_text(
            "© Source: @Patrick_Botz"
        )


        await msg.delete()


    except Exception as e:

        print("IMG ERROR:", e)

        try:
            await msg.delete()
        except:
            pass

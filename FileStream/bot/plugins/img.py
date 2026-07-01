from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import re
import asyncio


TMDB_API = "18303910643c603ebb9e370f2f49db56"


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
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={search_name}"
            )

            async with session.get(search_url) as resp:
                search = await resp.json()


            results = [
                x for x in search.get("results", [])
                if x.get("media_type") in ["movie","tv"]
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


            media_type = movie.get("media_type","movie")
            movie_id = movie["id"]


            image_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{movie_id}/images"
                f"?include_image_language=en,null,hi"
                f"&api_key={TMDB_API}"
            )


            async with session.get(image_url) as resp:
                data = await resp.json()



        images = []
        hindi = []


        # Main poster
        if movie.get("poster_path"):
            images.append(
                "https://image.tmdb.org/t/p/original"
                + movie["poster_path"]
            )


        # Backdrop
        if movie.get("backdrop_path"):
            images.append(
                "https://image.tmdb.org/t/p/original"
                + movie["backdrop_path"]
            )


        # Posters filter
        for x in data.get("posters", []):

            lang = x.get("iso_639_1")

            img = (
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )

            if lang in ["en", None]:
                images.append(img)

            elif lang == "hi":
                hindi.append(img)



        # Backdrops add
        for x in data.get("backdrops", []):

            if x.get("file_path"):
                images.append(
                    "https://image.tmdb.org/t/p/original"
                    + x["file_path"]
                )


        # remove duplicate
        images = list(dict.fromkeys(images))[:20]
        hindi = list(dict.fromkeys(hindi))[:5]


        await msg.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(images)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        # main 20 images
        for i in range(0, len(images), 10):

            album = []

            for pic in images[i:i+10]:
                album.append(
                    InputMediaPhoto(
                        media=pic
                    )
                )


            try:
                await client.send_media_group(
                    chat_id=message.chat.id,
                    media=album,
                    reply_to_message_id=message.id
                )

            except Exception as e:
                if "topics" not in str(e) and "Messages.init" not in str(e):
                    raise e


            await asyncio.sleep(1)



        # extra Hindi posters
        if hindi:

            album = []

            for pic in hindi:
                album.append(
                    InputMediaPhoto(media=pic)
                )

            await client.send_media_group(
                chat_id=message.chat.id,
                media=album,
                reply_to_message_id=message.id
            )


        await message.reply_text(
            f"🖼️ <b>IMAGES FOR:</b> {name}\n\n"
            f"• <b>SOURCE:</b> @Patrick_Botz"
        )


        await msg.delete()


    except Exception as e:
        await msg.edit(
            f"❌ RESULT ERROR\n\n{e}"
            )

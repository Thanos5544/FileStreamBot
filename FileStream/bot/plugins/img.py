from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name year"
        )

    name = " ".join(message.command[1:])

    msg = await message.reply_text(
        "⬆️ Uᴘʟᴏᴀᴅɪɴɢ 20 ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
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
                return await msg.edit("❌ Not Found")


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

        # posters first
        for x in data.get("posters", [])[:20]:
            images.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


        # backdrops after
        for x in data.get("backdrops", [])[:20]:
            images.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


        if movie.get("poster_path"):
            images.insert(
                0,
                "https://image.tmdb.org/t/p/original"
                + movie["poster_path"]
            )


        images = list(dict.fromkeys(images))[:20]


        # 5-5 album
        for i in range(0, len(images), 5):

            album = []

            for img in images[i:i+5]:
                album.append(
                    InputMediaPhoto(img)
                )

            await message.reply_media_group(album)


        title = movie.get("title") or movie.get("name")
        year = (
            movie.get("release_date","")[:4]
            or movie.get("first_air_date","")[:4]
        )

        await message.reply_text(
            f"🖼 <b>IMAGES FOR:</b> {title} {year}\n\n"
            f"• Source: @Patrick_Botz",
            parse_mode="html"
        )

        await msg.delete()


    except Exception as e:
        await msg.edit(
            f"❌ RESULT ERROR\n\n{str(e)}"
        )

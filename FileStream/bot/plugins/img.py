from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import re


TMDB_API = "18303910643c603ebb9e370f2f49db56"
BASE = "https://image.tmdb.org/t/p/original"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name year"
        )


    name = " ".join(message.command[1:])


    year = None
    match = re.search(r"(19|20)\d{2}", name)

    if match:
        year = match.group()
        name = name.replace(year, "").strip()


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


            results = search.get("results", [])


            if year:
                results = [
                    x for x in results
                    if year in (
                        x.get("release_date","")
                        or x.get("first_air_date","")
                    )
                ]


            if not results:
                return await msg.edit("❌ Not Found")


            movie = results[0]

            media_type = movie.get("media_type","movie")
            movie_id = movie["id"]


            img_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{movie_id}/images"
                f"?api_key={TMDB_API}"
            )


            async with session.get(img_url) as resp:
                data = await resp.json()



        images = []


        if movie.get("poster_path"):
            images.append(
                BASE + movie["poster_path"]
            )


        if movie.get("backdrop_path"):
            images.append(
                BASE + movie["backdrop_path"]
            )


        # Backdrops
        for x in data.get("backdrops", []):
            images.append(
                BASE + x["file_path"]
            )


        # Posters extra
        for x in data.get("posters", []):
            images.append(
                BASE + x["file_path"]
            )


        # remove repeat + max 20
        images = list(dict.fromkeys(images))[:20]


        if not images:
            return await msg.edit("❌ Images Not Found")


        await msg.edit(
            "⬆️ Uᴘʟᴏᴀᴅɪɴɢ 20 ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        title = (
            movie.get("title")
            or movie.get("name")
            or name
        )


        caption = (
            f"🖼 Iᴍᴀɢᴇs ғᴏʀ: {title}\n\n"
            "◍ Sᴏᴜʀᴄᴇ: @Patrick_Botz"
        )


        for i in range(0, len(images), 10):

            album = []


            for img in images[i:i+10]:

                album.append(
                    InputMediaPhoto(
                        img,
                        caption=caption if i == 0 and len(album) == 0 else None
                    )
                )


            await message.reply_media_group(album)


        await msg.delete()


    except Exception as e:
        await msg.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

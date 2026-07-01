from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio


TMDB_API = "18303910643c603ebb9e370f2f49db56"
TMDB_IMG = "https://image.tmdb.org/t/p/original"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name"
        )

    name = " ".join(message.command[1:])

    msg = await message.reply_text(
        "🔎 Fetching HD Posters..."
    )

    try:

        async with aiohttp.ClientSession() as session:

            search_url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(search_url) as r:
                search = await r.json()


            results = search.get("results", [])

            if not results:
                await msg.edit("❌ Not Found")
                return


            item = results[0]

            media_type = item.get(
                "media_type",
                "movie"
            )

            media_id = item["id"]


            images_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{media_id}/images"
                f"?api_key={TMDB_API}"
            )


            async with session.get(images_url) as r:
                data = await r.json()



        posters = []
        backdrops = []


        # Main poster
        if item.get("poster_path"):
            posters.append(
                TMDB_IMG + item["poster_path"]
            )


        # All posters
        for p in data.get("posters", []):

            url = TMDB_IMG + p["file_path"]

            if url not in posters:
                posters.append(url)



        # Backdrops
        for b in data.get("backdrops", []):

            url = TMDB_IMG + b["file_path"]

            if url not in backdrops:
                backdrops.append(url)



        images = posters + backdrops


        if not images:
            await msg.edit(
                "❌ No Images Found"
            )
            return



        await msg.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(images)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )



        # Telegram max 10 photos per album
        for i in range(0, len(images), 10):

            album = []

            for pic in images[i:i+10]:
                album.append(
                    InputMediaPhoto(pic)
                )


            await message.reply_media_group(album)

            # avoid flood
            await asyncio.sleep(3)



        await msg.delete()



    except Exception as e:

        print("IMG ERROR:", e)

        try:
            await msg.delete()
        except:
            pass

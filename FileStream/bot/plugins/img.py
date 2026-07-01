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

    wait = await message.reply_text("🔎 Fetching HD Images...")

    try:
        async with aiohttp.ClientSession() as session:

            # multi search (movie + tv)
            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(url) as r:
                result = await r.json()


            if not result.get("results"):
                return await wait.edit("❌ Not Found")


            item = result["results"][0]

            media_type = item.get("media_type", "movie")
            mid = item["id"]


            # details with images
            imgurl = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{mid}/images"
                f"?api_key={TMDB_API}"
                "&include_image_language=en,null,hi"
            )

            async with session.get(imgurl) as r:
                data = await r.json()


        pics = []


        # Poster
        if item.get("poster_path"):
            pics.append(
                IMG + item["poster_path"]
            )


        # Backdrop
        if item.get("backdrop_path"):
            pics.append(
                IMG + item["backdrop_path"]
            )


        # Hindi posters first
        hindi = []

        for p in data.get("posters", []):

            if p.get("iso_639_1") == "hi":
                hindi.append(
                    IMG + p["file_path"]
                )


        pics.extend(hindi[:5])


        # all backdrops
        for b in data.get("backdrops", []):

            pics.append(
                IMG + b["file_path"]
            )


        # remove duplicate
        pics = list(dict.fromkeys(pics))


        if not pics:
            return await wait.edit("❌ Images not found")


        pics = pics[:25]


        await wait.delete()


        # Telegram max 10
        for i in range(0, len(pics), 10):

            album = []

            for x in pics[i:i+10]:
                album.append(
                    InputMediaPhoto(x)
                )

            await client.send_media_group(
                chat_id=message.chat.id,
                media=album
            )


            if i + 10 < len(pics):
                await asyncio.sleep(3)



    except Exception as e:

        await wait.edit(
            f"❌ ERROR\n\n{e}"
        )

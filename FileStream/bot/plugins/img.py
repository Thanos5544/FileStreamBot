from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio


TMDB_API = "18303910643c603ebb9e370f2f49db56"
IMG = "https://image.tmdb.org/t/p/original"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text("❌ Use:\n/img movie name year")

    query = " ".join(message.command[1:])

    status = await message.reply_text("🔎 Fetching Images...")


    try:
        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={query}"
            )

            async with session.get(url) as r:
                data = await r.json()


            if not data.get("results"):
                return await status.edit("❌ Not Found")


            item = data["results"][0]

            typ = item.get("media_type")

            if typ not in ["movie", "tv"]:
                typ = "movie"


            detail = (
                f"https://api.themoviedb.org/3/{typ}/"
                f"{item['id']}/images?api_key={TMDB_API}"
            )


            async with session.get(detail) as r:
                imgs = await r.json()



        pics = []


        # Poster
        if item.get("poster_path"):
            pics.append(IMG + item["poster_path"])


        # Backdrops
        for x in imgs.get("backdrops", []):
            pics.append(IMG + x["file_path"])


        # More posters
        for x in imgs.get("posters", []):
            pics.append(IMG + x["file_path"])



        pics = list(dict.fromkeys(pics))[:20]


        if not pics:
            return await status.edit("❌ Images Not Found")


        await status.edit(
            f"⬆️ Uploading {len(pics)} images to Telegram...\n\n"
            f"🖼 Source: @Patrick_Botz"
        )


        for i in range(0, len(pics), 10):

            media = [
                InputMediaPhoto(x)
                for x in pics[i:i+10]
            ]

            await message.reply_media_group(media)

            if i + 10 < len(pics):
                await asyncio.sleep(3)


        await status.delete()


    except Exception as e:
        await status.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

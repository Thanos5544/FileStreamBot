from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name year"
        )

    query = " ".join(message.command[1:])

    status = await message.reply_text(
        "🔎 Fetching Images..."
    )

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

            media_type = item.get("media_type")

            if media_type not in ["movie", "tv"]:
                media_type = "movie"

            mid = item["id"]


            img_url = (
                f"https://api.themoviedb.org/3/{media_type}/{mid}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(img_url) as r:
                imgs = await r.json()


        photos = []


        # poster first
        if item.get("poster_path"):
            photos.append(
                "https://image.tmdb.org/t/p/original"
                + item["poster_path"]
            )


        # backdrop
        if item.get("backdrop_path"):
            photos.append(
                "https://image.tmdb.org/t/p/original"
                + item["backdrop_path"]
            )


        # extra posters
        for p in imgs.get("posters", [])[:10]:
            photos.append(
                "https://image.tmdb.org/t/p/original"
                + p["file_path"]
            )


        # extra backdrops
        for b in imgs.get("backdrops", [])[:10]:
            photos.append(
                "https://image.tmdb.org/t/p/original"
                + b["file_path"]
            )


        photos = list(dict.fromkeys(photos))[:20]


        if not photos:
            return await status.edit("❌ Images Not Found")


        await status.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(photos)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        caption = (
            f"🖼 <b>IMAGES FOR:</b> {query}\n\n"
            f"• <b>Source:</b> @Patrick_Botz"
        )


        for i in range(0, len(photos), 10):

            media = []

            for x in photos[i:i+10]:
                media.append(
                    InputMediaPhoto(x)
                )

            if i == 10:
                await asyncio.sleep(3)

            await message.reply_media_group(media)


        await status.delete()


    except Exception as e:
        await status.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

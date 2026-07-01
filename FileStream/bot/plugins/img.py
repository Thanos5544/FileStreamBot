from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import re


TMDB_API = "18303910643c603ebb9e370f2f49db56"


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

        m = re.search(r"(19|20)\d{2}", name)

        if m:
            year = m.group()
            name = name.replace(year, "").strip()


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
                    if (
                        x.get("release_date", "")[:4] == year
                        or
                        x.get("first_air_date", "")[:4] == year
                    )
                ]


            if not results:
                return await msg.edit("❌ Not found")


            item = results[0]

            media_type = item.get(
                "media_type",
                "movie"
            )

            item_id = item["id"]


            image_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{item_id}/images"
                f"?api_key={TMDB_API}"
            )


            async with session.get(image_url) as resp:
                data = await resp.json()



        images = []


        for x in data.get("posters", [])[:10]:

            images.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


        for x in data.get("backdrops", [])[:15]:

            images.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


        images = list(dict.fromkeys(images))[:20]


        if not images:
            return await msg.edit(
                "❌ Images not found"
            )


        for i in range(0, len(images), 10):

            await message.reply_media_group(
                [
                    InputMediaPhoto(x)
                    for x in images[i:i+10]
                ]
            )


        await msg.delete()


    except Exception as e:
        await msg.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

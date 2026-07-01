from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp


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
        async with aiohttp.ClientSession() as session:

            # Search Movie
            search_url = (
                "https://api.themoviedb.org/3/search/movie"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(search_url) as resp:
                search = await resp.json()


            if not search.get("results"):
                return await msg.edit("❌ Movie not found")


            movie = search["results"][0]
            movie_id = movie["id"]


            # Movie Images
            image_url = (
                f"https://api.themoviedb.org/3/movie/{movie_id}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(image_url) as resp:
                data = await resp.json()


        images = []


        # Poster
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


        # More Backdrops
        for x in data.get("backdrops", [])[:18]:
            images.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


        images = list(dict.fromkeys(images))[:20]


        if not images:
            return await msg.edit("❌ Images not found")


        media = []

        for img in images:
            media.append(
                InputMediaPhoto(img)
            )


        await message.reply_media_group(
            media
        )

        await msg.delete()


    except Exception as e:
        await msg.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

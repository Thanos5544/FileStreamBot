from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio
import re
import io

TMDB_API = "18303910643c603ebb9e370f2f49db56"
IMG = "https://image.tmdb.org/t/p/original"


async def download_image(session, url):
    async with session.get(url) as r:
        return io.BytesIO(await r.read())


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text("❌ Use:\n/img name year")

    query = " ".join(message.command[1:])

    year = None
    match = re.search(r"(19|20)\d{2}", query)

    if match:
        year = match.group()
        query = query.replace(year, "").strip()

    wait = await message.reply_text("🔎 Fetching HD Images...")

    try:
        async with aiohttp.ClientSession() as session:

            # search movie / series
            search_url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={query}"
            )

            async with session.get(search_url) as r:
                data = await r.json()

            results = data.get("results", [])

            if year:
                results = [
                    x for x in results
                    if year in (x.get("release_date", "") or x.get("first_air_date", ""))
                ]

            if not results:
                return await wait.edit("❌ Not Found")

            item = results[0]
            media_type = item.get("media_type", "movie")
            mid = item["id"]

            # images API
            img_url = (
                f"https://api.themoviedb.org/3/{media_type}/{mid}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(img_url) as r:
                imgs = await r.json()

            photos = []

            # poster
            if item.get("poster_path"):
                photos.append(IMG + item["poster_path"])

            # backdrops
            for x in imgs.get("backdrops", []):
                path = x.get("file_path")
                if path:
                    photos.append(IMG + path)

            # remove duplicates + limit 20
            photos = list(dict.fromkeys(photos))[:20]

            if not photos:
                return await wait.edit("❌ Images not found")

            await wait.delete()

            # send in batches of 10
            for i in range(0, len(photos), 10):

                media = []

                for p in photos[i:i+10]:
                    img_bytes = await download_image(session, p)
                    img_bytes.seek(0)
                    media.append(InputMediaPhoto(img_bytes))

                await message.reply_media_group(media)

                await asyncio.sleep(2)

    except Exception as e:
        await wait.edit(f"❌ ERROR\n\n{e}")

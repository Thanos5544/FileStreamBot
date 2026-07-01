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


    status = await message.reply_text(
        "⬆️ Uᴘʟᴏᴀᴅɪɴɢ 20 ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
    )


    try:
        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={query}"
            )

            async with session.get(url) as r:
                data = await r.json()


            results = data.get("results", [])


            if year:
                results = [
                    x for x in results
                    if year in (
                        x.get("release_date","")
                        or x.get("first_air_date","")
                    )
                ]


            if not results:
                return await status.edit("❌ Not Found")


            item = results[0]
            media_type = item.get("media_type","movie")
            mid = item["id"]


            img_api = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{mid}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(img_api) as r:
                imgs = await r.json()


            photos = []

            if item.get("poster_path"):
                photos.append(IMG + item["poster_path"])


            for x in imgs.get("backdrops", []):
                photos.append(IMG + x["file_path"])


            photos = list(dict.fromkeys(photos))[:20]


            if not photos:
                return await status.edit("❌ Images Not Found")


            await status.delete()


            title = (
                item.get("title")
                or item.get("name")
                or query
            )


            caption = (
                f"🖼 Iᴍᴀɢᴇs ғᴏʀ: {title}\n\n"
                "◍ Sᴏᴜʀᴄᴇ: @Patrick_Botz"
            )


            for i in range(0, len(photos), 10):

                album = []

                for p in photos[i:i+10]:
                    img = await download_image(session, p)
                    img.seek(0)

                    album.append(
                        InputMediaPhoto(
                            img,
                            caption=caption if i == 0 and len(album)==0 else None
                        )
                    )


                await message.reply_media_group(album)

                await asyncio.sleep(1)


    except Exception as e:
        await status.edit(f"❌ ERROR\n{e}")

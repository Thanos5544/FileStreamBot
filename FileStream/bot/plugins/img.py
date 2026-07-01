from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie year"
        )

    query = " ".join(message.command[1:])

    wait = await message.reply_text(
        "🔎 Fetching Posters..."
    )

    try:
        async with aiohttp.ClientSession() as session:

            search = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={query}"
            )

            async with session.get(search) as r:
                data = await r.json()


            if not data.get("results"):
                return await wait.edit("❌ Not Found")


            item = data["results"][0]

            media = item.get("media_type")

            if media not in ["movie", "tv"]:
                media = "movie"


            img_api = (
                f"https://api.themoviedb.org/3/"
                f"{media}/{item['id']}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(img_api) as r:
                imgs = await r.json()



        base = "https://image.tmdb.org/t/p/original"

        posters = []


        if item.get("poster_path"):
            posters.append(
                base + item["poster_path"]
            )


        for p in imgs.get("posters", [])[:40]:
            posters.append(
                base + p["file_path"]
            )


        posters = list(dict.fromkeys(posters))[:20]


        if not posters:
            return await wait.edit(
                "❌ Posters Not Found"
            )


        await wait.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(posters)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        caption = f"""
🖼 **IMAGES FOR:** {query}

• **SOURCE:** @Patrick_Botz
"""


        for i in range(0, len(posters), 10):

            album = []

            for x in posters[i:i+10]:

                album.append(
                    InputMediaPhoto(
                        x,
                        caption=caption if len(album)==0 else None
                    )
                )


            await client.send_media_group(
                chat_id=message.chat.id,
                media=album
            )

            await asyncio.sleep(3)


        await wait.delete()


    except Exception as e:

        await wait.edit(
            f"❌ RESULT ERROR\n\n{e}"
        )

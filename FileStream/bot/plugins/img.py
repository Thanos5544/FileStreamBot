import aiohttp
import asyncio

from pyrogram import filters
from pyrogram.types import InputMediaPhoto

from FileStream.bot import FileStream


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@FileStream.on_message(filters.command("img"))
async def img_search(_, m):

    if len(m.command) < 2:
        return await m.reply_text(
            "❌ ᴜsᴇ:\n\n/img movie name"
        )

    name = " ".join(m.command[1:])

    wait = await m.reply_text(
        "🔎 Sᴇᴀʀᴄʜɪɴɢ..."
    )

    try:

        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(url) as r:
                data = await r.json()


        results = data.get("results", [])

        if not results:
            return await wait.edit_text(
                "❌ Nᴏ Rᴇsᴜʟᴛ Fᴏᴜɴᴅ"
            )


        item = results[0]

        typ = item.get("media_type")
        mid = item.get("id")


        async with aiohttp.ClientSession() as session:

            url = (
                f"https://api.themoviedb.org/3/{typ}/{mid}"
                f"?api_key={TMDB_API}&append_to_response=images"
            )

            async with session.get(url) as r:
                info = await r.json()


        pics = []

        for x in info.get("images", {}).get("backdrops", []):
            pics.append(
                "https://image.tmdb.org/t/p/w780"
                + x["file_path"]
            )


        for x in info.get("images", {}).get("posters", []):
            pics.append(
                "https://image.tmdb.org/t/p/w780"
                + x["file_path"]
            )


        pics = pics[:20]


        if not pics:
            return await wait.edit_text(
                "❌ Iᴍᴀɢᴇ Nᴏᴛ Fᴏᴜɴᴅ"
            )


        media = [
            InputMediaPhoto(p)
            for p in pics
        ]


        await m.reply_media_group(media)

        await wait.delete()


    except Exception as e:
        print(e)
        await wait.edit_text(
            "❌ Rᴇsᴜʟᴛ Eʀʀᴏʀ"
        )

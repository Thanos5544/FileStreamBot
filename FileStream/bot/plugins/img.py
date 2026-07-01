from FileStream.bot import FileStream

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)

import aiohttp


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@FileStream.on_message(filters.command("img"))
async def img(_, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name"
        )

    name = " ".join(message.command[1:])

    msg = await message.reply_text(
        "🔎 Searching..."
    )

    try:
        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(url) as resp:
                data = await resp.json()


        results = data.get("results", [])[:5]

        if not results:
            return await msg.edit("❌ Not Found")


        buttons = []

        for item in results:

            title = item.get("title") or item.get("name")

            year = (
                item.get("release_date")
                or item.get("first_air_date")
                or ""
            )[:4]

            typ = item.get("media_type")

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"🎬 {title} {year}",
                        callback_data=f"img:{typ}:{item['id']}"
                    )
                ]
            )


        await msg.edit(
            "👇 Select:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


    except Exception as e:
        await msg.edit(
            f"❌ Search Error\n{e}"
        )



@FileStream.on_callback_query(filters.regex(r"^img:"))
async def send_images(_, query):

    _, typ, mid = query.data.split(":")

    await query.answer("📸 Fetching HD Images...")


    try:

        async with aiohttp.ClientSession() as session:

            url = (
                f"https://api.themoviedb.org/3/{typ}/{mid}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(url) as resp:
                data = await resp.json()


        pics = []


        for x in data.get("posters", [])[:10]:

            pics.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


        for x in data.get("backdrops", [])[:10]:

            pics.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


        pics = list(dict.fromkeys(pics))


        if not pics:
            return await query.message.edit(
                "❌ Images not found"
            )


        for i in range(0, len(pics), 10):

            await query.message.reply_media_group(
                [
                    InputMediaPhoto(x)
                    for x in pics[i:i+10]
                ]
            )


        await query.message.delete()


    except Exception as e:
        await query.message.edit(
            f"❌ Image Error\n{e}"
        )

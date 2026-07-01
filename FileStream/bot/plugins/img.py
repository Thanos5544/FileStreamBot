from FileStream.bot import FileStream

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

import aiohttp
import asyncio
import re


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

        year = None

        m = re.search(r"(19|20)\d{2}", name)

        if m:
            year = m.group()
            name = name.replace(year, "").strip()


        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )


            async with session.get(url) as r:
                data = await r.json()


        results = data.get("results", [])


        if year:

            results = [
                x for x in results
                if (
                    x.get("release_date","")[:4] == year
                    or
                    x.get("first_air_date","")[:4] == year
                )
            ]


        if not results:
            return await msg.edit(
                "❌ Movie/Series not found"
            )


        item = results[0]

        typ = item.get(
            "media_type",
            "movie"
        )

        mid = item["id"]


        await msg.edit(
            f"🎬 {item.get('title') or item.get('name')}\n\nChoose 👇",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🌄 Landscape",
                            callback_data=f"imgland:{typ}:{mid}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🖼 Poster",
                            callback_data=f"imgpost:{typ}:{mid}"
                        )
                    ]
                ]
            )
        )


    except Exception as e:
        await msg.edit(
            f"❌ Search Error\n{e}"
        )



async def get_images(typ, mid, mode):

    async with aiohttp.ClientSession() as session:

        url = (
            f"https://api.themoviedb.org/3/{typ}/{mid}/images"
            f"?api_key={TMDB_API}"
        )

        async with session.get(url) as r:
            data = await r.json()


    images = []


    if mode == "land":

        for x in data.get("backdrops", [])[:20]:

            images.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


    else:

        for x in data.get("posters", [])[:20]:

            images.append(
                "https://image.tmdb.org/t/p/original"
                + x["file_path"]
            )


    return images



@FileStream.on_callback_query(
    filters.regex(r"^img(land|post):")
)
async def send_images(_, query):

    mode, typ, mid = query.data.split(":")

    await query.answer(
        "📸 Fetching HD Images..."
    )


    try:

        images = await get_images(
            typ,
            mid,
            "land" if mode=="imgland" else "post"
        )


        if not images:
            return await query.message.edit(
                "❌ Images not found"
            )


        await query.message.delete()


        for img in images[:10]:

            await query.message.reply_photo(
                img
            )


        await asyncio.sleep(3)


        for img in images[10:20]:

            await query.message.reply_photo(
                img
            )


    except Exception as e:

        await query.message.reply_text(
            f"❌ RESULT ERROR\n{e}"
        )

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)
import aiohttp


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name"
        )

    name = " ".join(message.command[1:])

    msg = await message.reply_text("🔎 Searching...")


    async with aiohttp.ClientSession() as session:

        url = (
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_API}&query={name}"
        )

        async with session.get(url) as resp:
            data = await resp.json()


    results = data.get("results", [])[:5]


    if not results:
        return await msg.edit("❌ Not found")


    buttons = []

    for m in results:

        title = m.get("title") or m.get("name")
        year = (
            m.get("release_date")
            or m.get("first_air_date")
            or ""
        )[:4]

        buttons.append([
            InlineKeyboardButton(
                f"🎬 {title} {year}",
                callback_data=f"getimg:{m['media_type']}:{m['id']}"
            )
        ])


    await msg.edit(
        "👇 Choose Movie:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )



@Client.on_callback_query(filters.regex(r"getimg:"))
async def getimg(client, query):

    _, typ, mid = query.data.split(":")

    await query.message.edit("📸 Fetching images...")


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


    pics = pics[:20]


    for i in range(0, len(pics), 10):

        await client.send_media_group(
            query.message.chat.id,
            [
                InputMediaPhoto(x)
                for x in pics[i:i+10]
            ]
        )


    await query.message.delete()

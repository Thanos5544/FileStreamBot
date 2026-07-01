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


    async with aiohttp.ClientSession() as session:

        url = (
            "https://api.themoviedb.org/3/search/movie"
            f"?api_key={TMDB_API}&query={name}"
        )

        async with session.get(url) as r:
            data = await r.json()


        if not data.get("results"):
            return await msg.edit("❌ Movie not found")


        movie = data["results"][0]
        movie_id = movie["id"]


    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🖼 Posters",
                    callback_data=f"imgpost:{movie_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🌄 Backdrops",
                    callback_data=f"imgback:{movie_id}"
                )
            ]
        ]
    )


    await msg.edit(
        f"🎬 **{movie.get('title')}**\n\nChoose Image Type 👇",
        reply_markup=buttons
    )



async def get_images(movie_id):

    async with aiohttp.ClientSession() as session:

        url = (
            f"https://api.themoviedb.org/3/movie/{movie_id}/images"
            f"?api_key={TMDB_API}"
        )

        async with session.get(url) as r:
            data = await r.json()


    imgs = []


    for p in data.get("posters", [])[:20]:
        imgs.append(
            "https://image.tmdb.org/t/p/original"
            + p["file_path"]
        )


    return imgs



@FileStream.on_callback_query(filters.regex(r"^imgpost:"))
async def poster(_, query):

    movie_id = query.data.split(":")[1]

    await query.answer("Fetching Posters...")


    imgs = await get_images(movie_id)


    media = [
        InputMediaPhoto(x)
        for x in imgs[:10]
    ]


    await query.message.reply_media_group(media)



@FileStream.on_callback_query(filters.regex(r"^imgback:"))
async def backdrops(_, query):

    movie_id = query.data.split(":")[1]

    await query.answer("Fetching Backdrops...")


    async with aiohttp.ClientSession() as session:

        url = (
            f"https://api.themoviedb.org/3/movie/{movie_id}/images"
            f"?api_key={TMDB_API}"
        )

        async with session.get(url) as r:
            data = await r.json()


    imgs = []

    for p in data.get("backdrops", [])[:20]:

        imgs.append(
            "https://image.tmdb.org/t/p/original"
            + p["file_path"]
        )


    media = [
        InputMediaPhoto(x)
        for x in imgs[:10]
    ]


    await query.message.reply_media_group(media)

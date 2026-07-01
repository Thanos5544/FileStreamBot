import aiohttp

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)

from FileStream.bot import FileStream


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@FileStream.on_message(filters.command("img"))
async def img_search(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ ᴜsᴇ:\n\n/img movie name"
        )

    query = " ".join(message.command[1:])

    msg = await message.reply_text(
        "🔎 sᴇᴀʀᴄʜɪɴɢ..."
    )

    try:

        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={query}"
            )

            async with session.get(url) as resp:
                data = await resp.json()


        results = data.get("results", [])[:10]


        if not results:
            return await msg.edit_text(
                "❌ ɴᴏ ʀᴇsᴜʟᴛ ғᴏᴜɴᴅ"
            )


        buttons = []


        for item in results:

            title = (
                item.get("title")
                or
                item.get("name")
                or
                "Unknown"
            )

            typ = item.get("media_type")
            mid = item.get("id")


            buttons.append(
                [
                    InlineKeyboardButton(
                        title,
                        callback_data=f"img|{typ}|{mid}"
                    )
                ]
            )


        await msg.edit_text(
            "🎬 sᴇʟᴇᴄᴛ ᴛɪᴛʟᴇ 👇",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


    except Exception as e:
        print(e)

        await msg.edit_text(
            "❌ ʀᴇsᴜʟᴛ ᴇʀʀᴏʀ"
        )




@FileStream.on_callback_query(
    filters.regex("^img\\|")
)
async def img_callback(client, query):

    await query.answer(
        "📸 ɢᴇᴛᴛɪɴɢ ɪᴍᴀɢᴇs..."
    )


    _, typ, mid = query.data.split("|")


    try:

        async with aiohttp.ClientSession() as session:

            url = (
                f"https://api.themoviedb.org/3/{typ}/{mid}"
                f"?api_key={TMDB_API}&append_to_response=images"
            )

            async with session.get(url) as resp:
                data = await resp.json()



        images = []


        for x in data.get("images", {}).get("backdrops", []):

            images.append(
                "https://image.tmdb.org/t/p/w780"
                +
                x["file_path"]
            )


        for x in data.get("images", {}).get("posters", []):

            images.append(
                "https://image.tmdb.org/t/p/w780"
                +
                x["file_path"]
            )


        images = images[:20]


        if not images:
            return await query.message.reply_text(
                "❌ ɪᴍᴀɢᴇ ɴᴏᴛ ғᴏᴜɴᴅ"
            )


        media = []

        for pic in images:

            media.append(
                InputMediaPhoto(pic)
            )


        await query.message.reply_media_group(
            media
        )


    except Exception as e:

        print(e)

        await query.message.reply_text(
            "❌ ɪᴍᴀɢᴇ ᴇʀʀᴏʀ"
        )

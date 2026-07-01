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
async def img_search(_, m):

    if len(m.command) < 2:
        return await m.reply_text(
            "❌ ᴜsᴇ:\n\n/img movie name"
        )

    name = " ".join(m.command[1:])

    msg = await m.reply_text(
        "🔎 sᴇᴀʀᴄʜɪɴɢ..."
    )

    try:

        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(url) as r:
                data = await r.json()


        results = data.get("results", [])[:8]


        if not results:
            return await msg.edit_text(
                "❌ ɴᴏ ʀᴇsᴜʟᴛ"
            )


        buttons = []


        for x in results:

            title = x.get("title") or x.get("name")

            typ = x.get("media_type")

            if typ not in ["movie","tv"]:
                continue


            buttons.append(
                [
                    InlineKeyboardButton(
                        f"🎬 {title}",
                        callback_data=f"img#{typ}#{x['id']}"
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
            "❌ sᴇᴀʀᴄʜ ᴇʀʀᴏʀ"
        )




@FileStream.on_callback_query(filters.regex("^img#"))
async def img_callback(_, q):

    await q.answer("📸 ɢᴇɴᴇʀᴀᴛɪɴɢ...")


    try:

        _, typ, mid = q.data.split("#")


        async with aiohttp.ClientSession() as session:

            url = (
                f"https://api.themoviedb.org/3/{typ}/{mid}"
                f"?api_key={TMDB_API}"
            )

            async with session.get(url) as r:
                info = await r.json()



            imgurl = (
                f"https://api.themoviedb.org/3/{typ}/{mid}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(imgurl) as r:
                images = await r.json()



        pics = []


        if info.get("poster_path"):
            pics.append(
                "https://image.tmdb.org/t/p/w780"
                + info["poster_path"]
            )


        if info.get("backdrop_path"):
            pics.append(
                "https://image.tmdb.org/t/p/w780"
                + info["backdrop_path"]
            )


        for x in images.get("posters", []):
            pics.append(
                "https://image.tmdb.org/t/p/w780"
                + x["file_path"]
            )


        for x in images.get("backdrops", []):
            pics.append(
                "https://image.tmdb.org/t/p/w780"
                + x["file_path"]
            )


        pics = list(dict.fromkeys(pics))[:20]


        if not pics:
            return await q.message.reply_text(
                "❌ ɪᴍᴀɢᴇ ɴᴏᴛ ғᴏᴜɴᴅ"
            )


        await q.message.reply_media_group(
            [
                InputMediaPhoto(media=p)
                for p in pics
            ]
        )


    except Exception as e:
        print(e)

        await q.message.reply_text(
            "❌ ɪᴍᴀɢᴇ ᴇʀʀᴏʀ"
        )

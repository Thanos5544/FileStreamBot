from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp


TMDB_API = "18303910643c603ebb9e370f2f49db56"


@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text("❌ Use:\n/img movie name")

    name = " ".join(message.command[1:])

    status = await message.reply_text("🔎 Fetching HD Images...")

    try:
        async with aiohttp.ClientSession() as session:

            url = (
                "https://api.themoviedb.org/3/search/multi"
                f"?api_key={TMDB_API}&query={name}"
            )

            async with session.get(url) as r:
                data = await r.json()

            if not data.get("results"):
                return await status.edit("❌ Not Found")

            item = data["results"][0]

            media_type = item.get("media_type", "movie")
            mid = item["id"]


            img_url = (
                f"https://api.themoviedb.org/3/"
                f"{media_type}/{mid}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(img_url) as r:
                imgs = await r.json()


        photos = []


        base = "https://image.tmdb.org/t/p/original"


        # Posters first
        for x in imgs.get("posters", []):
            photos.append(base + x["file_path"])


        # Backdrops
        for x in imgs.get("backdrops", []):
            photos.append(base + x["file_path"])


        # Still images
        for x in imgs.get("stills", []):
            photos.append(base + x["file_path"])


        # remove duplicate
        photos = list(dict.fromkeys(photos))


        # only 20
        photos = photos[:20]


        if not photos:
            return await status.edit("❌ No Images Found")


        await status.edit(
            f"⬆️ Uᴘʟᴏᴀᴅɪɴɢ {len(photos)} ɪᴍᴀɢᴇs ᴛᴏ Tᴇʟᴇɢʀᴀᴍ..."
        )


        for i in range(0, len(photos), 10):

            media = []

            for p in photos[i:i+10]:
                media.append(
                    InputMediaPhoto(p)
                )

            await message.reply_media_group(media)


        await message.reply_text(
            f"🖼️ <b>IMAGES FOR:</b> {name}\n\n"
            f"• Source: @Patrick_Botz"
        )


        await status.delete()


    except Exception as e:
        await status.edit(
            "❌ RESULT ERROR"
        )

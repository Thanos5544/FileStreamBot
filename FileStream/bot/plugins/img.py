import aiohttp

from pyrogram import filters
from pyrogram.types import InputMediaPhoto

from FileStream.bot import FileStream


ACCESS_KEY = "99JuNaSj-p9GZio8IAUtXTpsk_ySalCFrJ1GxU0EvtM"


@FileStream.on_message(filters.command("img"))
async def img_search(_, m):

    if len(m.command) < 2:
        return await m.reply_text(
            "❌ USE:\n\n/img movie name"
        )

    query = " ".join(m.command[1:])


    msg = await m.reply_text(
        "⬆️ Uploading 20 images to Telegram..."
    )


    try:

        url = (
            "https://api.unsplash.com/search/photos"
            f"?query={query}"
            "&per_page=20"
            f"&client_id={ACCESS_KEY}"
        )


        async with aiohttp.ClientSession() as session:

            async with session.get(url) as resp:

                data = await resp.json()


        results = data.get("results", [])


        if not results:

            return await msg.edit_text(
                "❌ No Images Found"
            )


        media = []


        for item in results[:20]:

            photo = item["urls"]["regular"]

            media.append(
                InputMediaPhoto(photo)
            )


        await m.reply_media_group(media)


        await m.reply_text(
f"""
🖼 **IMAGES FOR:** `{query}`

• SOURCE: Unsplash
"""
        )


        await msg.delete()


    except Exception as e:

        print(e)

        await msg.edit_text(
            "❌ RESULT ERROR"
        )

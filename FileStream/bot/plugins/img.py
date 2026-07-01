from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import aiohttp
import asyncio
import re


TMDB_API = "18303910643c603ebb9e370f2f49db56"
IMG = "https://image.tmdb.org/t/p/original"


async def tmdb_search(name):

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
        for x in results:
            date = (
                x.get("release_date")
                or
                x.get("first_air_date")
                or ""
            )

            if date.startswith(year):
                return x


    return results[0] if results else None



async def get_imgs(item):

    typ = item.get("media_type","movie")
    mid = item["id"]


    async with aiohttp.ClientSession() as session:

        url = (
            f"https://api.themoviedb.org/3/"
            f"{typ}/{mid}/images"
            f"?api_key={TMDB_API}"
            "&include_image_language=en,null,hi"
        )


        async with session.get(url) as r:
            data = await r.json()


    imgs=[]


    # poster
    if item.get("poster_path"):
        imgs.append(
            IMG + item["poster_path"]
        )


    # backdrops
    for x in data.get("backdrops",[]):
        imgs.append(
            IMG+x["file_path"]
        )


    # posters
    for x in data.get("posters",[]):
        imgs.append(
            IMG+x["file_path"]
        )


    return list(dict.fromkeys(imgs))[:20]



async def send_album(client, chat, imgs):

    media=[]

    for x in imgs:
        media.append(
            InputMediaPhoto(x)
        )


    if media:
        await client.send_media_group(
            chat,
            media
        )



@Client.on_message(filters.command("img"))
async def img(client,message):

    if len(message.command)<2:
        return await message.reply(
            "/img movie name year"
        )


    name=" ".join(message.command[1:])

    m=await message.reply("🔎 Searching...")


    try:

        item=await tmdb_search(name)


        if not item:
            return await m.edit("❌ Not Found")


        imgs=await get_imgs(item)


        if not imgs:
            return await m.edit("❌ Images not found")


        await m.delete()


        await send_album(
            client,
            message.chat.id,
            imgs[:10]
        )


        await asyncio.sleep(3)


        await send_album(
            client,
            message.chat.id,
            imgs[10:20]
        )


    except Exception as e:

        await m.edit(
            f"❌ ERROR\n{e}"
        )

import aiohttp
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto

TMDB_API = "18303910643c603ebb9e370f2f49db56"

@Client.on_message(filters.command("img"))
async def img(client, message):

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Use:\n/img movie name year"
        )

    name = " ".join(message.command[1:])
    msg = await message.reply_text("🔎 Fetching HD Images...")

    try:
        # Year extract करना
        year = None
        match = re.search(r"(19|20)\d{2}", name)

        if match:
            year = match.group()
            search_name = name.replace(year, "").strip()
        else:
            search_name = name

        async with aiohttp.ClientSession() as session:
            # FIX: यहाँ 'www' की जगह सटीक API एंडपॉइंट 'api.themoviedb.org' का इस्तेमाल किया है
            search_url = (
                "https://themoviedb.org"
                f"?api_key={TMDB_API}&query={search_name}"
            )

            async with session.get(search_url) as resp:
                search = await resp.json()

            results = search.get("results", [])
            results = [r for r in results if r.get("media_type") in ["movie", "tv"]]

            if not results:
                return await msg.edit("❌ Not found")

            # Year matching लॉजिक
            movie = results[0]
            if year:
                for item in results:
                    date = item.get("release_date") or item.get("first_air_date")
                    if date and date.startswith(year):
                        movie = item
                        break

            media_type = movie.get("media_type")
            movie_id = movie.get("id")

            # इमेजेस फेच करना
            image_url = (
                f"https://themoviedb.org{media_type}/{movie_id}/images"
                f"?api_key={TMDB_API}"
            )

            async with session.get(image_url) as resp:
                data = await resp.json()

        # इमेजेस कलेक्ट करना
        images = []

        if movie.get("poster_path"):
            images.append(f"https://tmdb.org{movie['poster_path']}")

        if movie.get("backdrop_path"):
            images.append(f"https://tmdb.org{movie['backdrop_path']}")

        for x in data.get("backdrops", []):
            images.append(f"https://tmdb.org{x['file_path']}")

        # यूनिक इमेजेस निकालना (अधिकतम 20)
        unique_images = list(dict.fromkeys(images))[:20]

        if not unique_images:
            return await msg.edit("❌ No images found for this title.")

        # 10-10 के ग्रुप में भेजना
        for i in range(0, len(unique_images), 10):
            album = []
            for img_url in unique_images[i:i+10]:
                album.append(InputMediaPhoto(media=img_url))
            
            # FIX: reply_media_group की जगह सीधे client.send_media_group का इस्तेमाल और क्रैश बाईपास
            try:
                await client.send_media_group(
                    chat_id=message.chat.id,
                    media=album,
                    reply_to_message_id=message.id
                )
            except Exception as media_err:
                # अगर 'topics' या 'Messages.init()' का इंटरनल लाइब्रेरी एरर आए तो उसे नजरअंदाज करें
                if "topics" in str(media_err) or "Messages" in str(media_err):
                    pass
                else:
                    raise media_err
            
            # टेलीग्राम फ्लडिंग से बचने के लिए छोटा सा डिले
            await asyncio.sleep(1)

        await msg.delete()

    except Exception as e:
        await msg.edit(f"❌ RESULT ERROR\n\n{e}")
        

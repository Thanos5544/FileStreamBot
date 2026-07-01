import os
import asyncio
import re
import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def get_yt_id(url):
    match = re.search(
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        url
    )
    return match.group(1) if match else None



@Client.on_message(
    filters.command("yt") |
    filters.regex(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/")
)
async def yt_download(client, message):

    url = message.text

    vid = get_yt_id(url)

    if not vid:
        return await message.reply_text(
            "❌ Invalid YouTube Link"
        )


    m = await message.reply_text(
        "🔎 Fetching YouTube Info..."
    )


    try:

        def get_info():

            opts = {
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True,
                "geo_bypass": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "android"
                        ]
                    }
                }
            }


            if os.path.exists("cookies.txt"):
                opts["cookiefile"] = "cookies.txt"


            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(
                    url,
                    download=False
                )


        data = await asyncio.to_thread(get_info)


        title = data.get(
            "title",
            "YouTube Video"
        )

        thumb = data.get("thumbnail")


        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎬 360p",
                        callback_data=f"yt|360|{vid}"
                    ),
                    InlineKeyboardButton(
                        "🎬 480p",
                        callback_data=f"yt|480|{vid}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎬 720p",
                        callback_data=f"yt|720|{vid}"
                    ),
                    InlineKeyboardButton(
                        "🎬 1080p",
                        callback_data=f"yt|1080|{vid}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎵 Audio",
                        callback_data=f"yt|audio|{vid}"
                    )
                ]
            ]
        )


        await message.reply_photo(
            photo=thumb,
            caption=f"🎥 <b>{title}</b>",
            reply_markup=buttons
        )

        await m.delete()


    except Exception as e:

        await m.edit(
            f"❌ Error\n{e}"
        )





@Client.on_callback_query(filters.regex("^yt"))
async def yt_download_file(client, query):

    _, quality, vid = query.data.split("|")


    url = (
        f"https://www.youtube.com/watch?v={vid}"
    )


    await query.message.edit_caption(
        "⬇️ Downloading..."
    )


    uid = query.from_user.id


    if quality == "audio":

        file = f"{uid}_{vid}.mp3"

        opts = {

            "format":
            "bestaudio/best",

            "outtmpl":
            f"{uid}_{vid}.%(ext)s",

            "postprocessors":
            [
                {
                    "key":
                    "FFmpegExtractAudio",

                    "preferredcodec":
                    "mp3",

                    "preferredquality":
                    "192"
                }
            ],

            "quiet": True
        }


    else:

        file = f"{uid}_{vid}.mp4"


        opts = {

            "format":
            f"bestvideo[height<={quality}]+bestaudio/best",

            "merge_output_format":
            "mp4",

            "outtmpl":
            file,

            "quiet": True
        }



    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"



    try:


        def download():

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])


        await asyncio.to_thread(download)



        await query.message.edit_caption(
            "⬆️ Uploading To Telegram..."
        )


        await query.message.reply_document(
            file,
            caption="✅ Downloaded by @Patrick_BotZ"
        )


        if os.path.exists(file):
            os.remove(file)


        await query.message.delete()



    except Exception as e:

        await query.message.edit_caption(
            f"❌ Failed\n{e}"
        )

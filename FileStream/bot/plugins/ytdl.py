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
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


@Client.on_message(filters.regex(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/"))
async def yt_download(client, message):

    url = message.text

    video_id = get_yt_id(url)

    if not video_id:
        return await message.reply_text(
            "❌ Invalid YouTube Link"
        )

    m = await message.reply_text(
        "🔎 Fetching YouTube Info..."
    )

    try:

        def info():
            with yt_dlp.YoutubeDL({
                "quiet": True,
                "no_warnings": True
            }) as ydl:
                return ydl.extract_info(
                    url,
                    download=False
                )

        data = await asyncio.to_thread(info)

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
                        callback_data=f"yt|360|{video_id}"
                    ),
                    InlineKeyboardButton(
                        "🎬 480p",
                        callback_data=f"yt|480|{video_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎬 720p",
                        callback_data=f"yt|720|{video_id}"
                    ),
                    InlineKeyboardButton(
                        "🎬 1080p",
                        callback_data=f"yt|1080|{video_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎵 Audio",
                        callback_data=f"yt|audio|{video_id}"
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

    _, quality, video_id = query.data.split("|")


    url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )


    await query.message.edit_caption(
        "⬇️ Downloading..."
    )


    uid = query.from_user.id


    if quality == "audio":

        file = f"{uid}.mp3"

        opts = {
            "format": "bestaudio/best",
            "outtmpl": file,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }
            ],
            "quiet": True
        }


    else:

        file = f"{uid}.mp4"

        opts = {
            "format":
            f"bestvideo[height<={quality}]+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": file,
            "quiet": True
        }



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
            caption="✅ Downloaded by @Patrick_Botz"
        )


        if os.path.exists(file):
            os.remove(file)


        await query.message.delete()


    except Exception as e:

        await query.message.edit_caption(
            f"❌ Download Failed\n{e}"
        )

        if os.path.exists(file):
            os.remove(file)

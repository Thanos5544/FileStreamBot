import asyncio
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid


async def send_msg(client, user_id, message, pin=False):
    try:
        sent = await message.copy(user_id)
        if pin:
            try:
                await client.pin_chat_message(user_id, sent.id)
            except Exception:
                pass
        return 200, None
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(client, user_id, message, pin)
    except UserIsBlocked:
        return 400, "blocked"
    except InputUserDeactivated:
        return 400, "deactivated"
    except PeerIdInvalid:
        return 400, "invalid"
    except Exception:
        return 500, "error"

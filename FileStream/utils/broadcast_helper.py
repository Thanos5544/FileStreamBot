import asyncio
import traceback
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    UserIsBlocked,
    PeerIdInvalid
)


async def send_msg(client, user_id, message, pin: bool = False):
    try:
        sent = await message.copy(chat_id=user_id)

        if pin:
            try:
                await client.pin_chat_message(
                    chat_id=user_id,
                    message_id=sent.id,
                    disable_notification=True
                )
            except Exception:
                pass

        return 200, None

    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(client, user_id, message, pin)

    except InputUserDeactivated:
        return 400, f"{user_id} : deactivated\n"

    except UserIsBlocked:
        return 400, f"{user_id} : blocked the bot\n"

    except PeerIdInvalid:
        return 400, f"{user_id} : user id invalid\n"

    except Exception:
        return 500, f"{user_id} : {traceback.format_exc()}\n"

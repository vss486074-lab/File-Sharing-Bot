#(©)CodeXBotz

import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import (
    ADMINS,
    FORCE_MSG,
    START_MSG,
    CUSTOM_CAPTION,
    DISABLE_CHANNEL_BUTTON,
    PROTECT_CONTENT,
    START_PIC,
    AUTO_DELETE_TIME,
    AUTO_DELETE_MSG,
    JOIN_REQUEST_ENABLE,
    FORCE_SUB_CHANNEL
)
from helper_func import subscribed, decode, get_messages, delete_file
from database.database import add_user, del_user, full_userbase, present_user


# ======================= START COMMAND ======================= #

@Bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):

    user_id = message.from_user.id

    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except:
            pass

    # -------- FORCE SUB CHECK -------- #
    if not await subscribed(client, message):
        invite = await client.create_chat_invite_link(
            chat_id=FORCE_SUB_CHANNEL,
            creates_join_request=JOIN_REQUEST_ENABLE
        )
        url = invite.invite_link

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔔 Join Channel", url=url)]]
        )

        await message.reply_text(
            FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=buttons,
            disable_web_page_preview=True
        )
        return
    # -------- START WITH ARGUMENT -------- #
    if len(message.command) > 1:
        try:
            decoded = await decode(message.command[1])
            args = decoded.split("-")
        except:
            return

        if len(args) == 3:
            start = int(int(args[1]) / abs(client.db_channel.id))
            end = int(int(args[2]) / abs(client.db_channel.id))
            ids = range(start, end + 1)
        elif len(args) == 2:
            ids = [int(int(args[1]) / abs(client.db_channel.id))]
        else:
            return

        wait = await message.reply_text("⏳ Please wait...")
        try:
            messages = await get_messages(client, ids)
        except:
            await wait.edit("❌ Failed to fetch messages")
            return
        await wait.delete()

        tracked = []

        for msg in messages:
            caption = (
                CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name
                )
                if CUSTOM_CAPTION and msg.document
                else "" if not msg.caption else msg.caption.html
            )

            try:
                copied = await msg.copy(
                    chat_id=message.chat.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    protect_content=PROTECT_CONTENT
                )

                if AUTO_DELETE_TIME and copied:
                    tracked.append(copied)

            except FloodWait as e:
                await asyncio.sleep(e.value)
            except:
                pass

        if tracked and AUTO_DELETE_TIME:
            info = await client.send_message(
                message.chat.id,
                AUTO_DELETE_MSG.format(time=AUTO_DELETE_TIME)
            )
            asyncio.create_task(delete_file(tracked, client, info))

        return

    # -------- NORMAL START -------- #
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📂 Send File", callback_data="send_file")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
    )

    if START_PIC:
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=buttons
        )
    else:
        await message.reply_text(
            START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=buttons
        )


# ======================= ADMIN COMMANDS ======================= #

WAIT_MSG = "<b>Processing ...</b>"
REPLY_ERROR = "<code>Reply to a message to broadcast.</code>"


@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await message.reply_text(WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"👥 Total users: <code>{len(users)}</code>")


@Bot.on_message(filters.command("broadcast") & filters.private & filters.user(ADMINS))
async def broadcast(client: Bot, message: Message):

    if not message.reply_to_message:
        msg = await message.reply_text(REPLY_ERROR)
        await asyncio.sleep(6)
        return await msg.delete()

    users = await full_userbase()
    sent = blocked = deleted = failed = 0

    status = await message.reply_text("📢 Broadcasting...")

    for user in users:
        try:
            await message.reply_to_message.copy(user)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except UserIsBlocked:
            await del_user(user)
            blocked += 1
        except InputUserDeactivated:
            await del_user(user)
            deleted += 1
        except:
            failed += 1

    await status.edit(
        f"""<b>📊 Broadcast Finished</b>

✅ Sent: <code>{sent}</code>
🚫 Blocked: <code>{blocked}</code>
🗑 Deleted: <code>{deleted}</code>
❌ Failed: <code>{failed}</code>
"""
    )

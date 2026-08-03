from asyncio import Future, sleep
from time import time

from aiohttp import ClientSession
from hypercorn.asyncio import serve
from hypercorn import Config as HypercornConfig
from pyrogram import filters
from pyrogram.errors import AuthKeyDuplicated, AuthKeyInvalid, SessionRevoked, SessionExpired
from pyrogram.methods.utilities.idle import idle
from pyrogram.storage import MemoryStorage
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from FileToLink import bot, Config, Strings
from FileToLink.archive import archive_msg
from FileToLink.server import app
from FileToLink.worker import Worker, AllWorkers, NotFound
from FileToLink.utils import participant


Last_Time = {}


@bot.on_message((filters.media | filters.document) & filters.private & filters.incoming)
async def main(_, msg: Message):
    await wait(msg.chat.id)

    if not await participant(msg.chat.id):
        return

    media = (msg.video or msg.document or msg.photo or msg.audio or
             msg.voice or msg.video_note or msg.sticker or msg.animation)

    if not media:
        return

    worker = AllWorkers.get(file_id=media.file_unique_id)
    if not worker:
        gen_msg = await bot.send_message(msg.chat.id, Strings.generating_link,
                                         reply_to_message_id=msg.id)

        archived_msg = await archive_msg(msg)
        worker = Worker(archived_msg)
        AllWorkers.add(worker)

        if archived_msg.id in NotFound:
            NotFound.remove(archived_msg.id)
    else:
        gen_msg = None

    name = worker.name
    dl_link = worker.link
    text = f"[{name}]({dl_link})"

    buttons = [[InlineKeyboardButton(Strings.dl_link, url=dl_link)]]
    if worker.stream:
        st_link = f'{dl_link}?st=1'
        buttons.append([InlineKeyboardButton(Strings.st_link, url=st_link)])
    reply_markup = InlineKeyboardMarkup(buttons)

    if gen_msg is not None:
        await gen_msg.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        await bot.send_message(msg.chat.id, text, reply_to_message_id=msg.id,
                               reply_markup=reply_markup, disable_web_page_preview=True)


async def wait(chat_id: int):
    if chat_id in Last_Time:
        x = time() - Last_Time[chat_id]
        if x < Config.Separate_Time:
            Last_Time[chat_id] += Config.Separate_Time
            await sleep(Config.Separate_Time - x)
        else:
            Last_Time[chat_id] = time()
    else:
        Last_Time[chat_id] = time()


@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    buttons = [[InlineKeyboardButton(Strings.dev_channel, url=f'https://t.me/shadow_bots')]]
    if Config.Bot_Channel:
        buttons.append([InlineKeyboardButton(Strings.bot_channel, url=f'https://t.me/{Config.Bot_Channel}')])
    await msg.reply_text(Strings.start, reply_markup=InlineKeyboardMarkup(buttons))


async def startup():
    try:
        await bot.start()
    except (AuthKeyDuplicated, AuthKeyInvalid, SessionRevoked, SessionExpired):
        bot.storage = MemoryStorage(":memory:")
        await bot.start()
    Config.Bot_UserName = (await bot.get_me()).username


if __name__ == '__main__':
    bot.loop.run_until_complete(startup())
    app_config = HypercornConfig()
    app_config._bind = [f'0.0.0.0:{Config.Port}']
    bot.loop.create_task(serve(app, app_config, shutdown_trigger=lambda: Future()))
    idle()

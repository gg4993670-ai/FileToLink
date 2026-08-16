from urllib.parse import unquote
import math
import asyncio

from pyrogram.errors import MessageIdInvalid
from quart import Quart, abort, request, Response, redirect

from FileToLink import Config, bot
from FileToLink.worker import Worker, AllWorkers, create_worker, NotFound

app = Quart("FileToLink-Bot")


@app.route('/')
async def root():
    return redirect("https://t.me/shadow_bots")


@app.route('/dl/<int:archive_id>/<path:name>')
async def download(archive_id: int, name: str):
    worker: Worker = AllWorkers.get(archive_id=archive_id)
    if worker is None:
        try:
            worker = await create_worker(archive_id)
        except (ValueError, MessageIdInvalid, Exception):
            NotFound.append(archive_id)
            return abort(404)

    name = unquote(name)
    file_size = worker.size
    message = worker.msg

    if not message:
        return abort(404)

    media = (
        message.video or
        message.document or
        message.photo or
        message.audio or
        message.voice or
        message.video_note or
        message.animation
    )

    if not media:
        return abort(404)

    range_header = request.headers.get("Range")
    
    if range_header:
        # Browser Range Request Parse
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0]) if byte_range[0] else 0
        end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
    else:
        start = 0
        end = file_size - 1

    end = min(end, file_size - 1)
    content_length = (end - start) + 1

    async def media_streamer():
        chunk_size = 1024 * 1024  # 1MB Pyrogram default
        first_part = math.floor(start / chunk_size)
        last_part = math.floor(end / chunk_size)

        current_part = first_part
        bytes_left = content_length

        try:
            async for chunk in bot.stream_media(message, offset=first_part):
                if current_part > last_part or bytes_left <= 0:
                    break

                # Chunk offset slicing
                chunk_start = (start % chunk_size) if current_part == first_part else 0
                chunk_data = chunk[chunk_start:]

                if len(chunk_data) > bytes_left:
                    chunk_data = chunk_data[:bytes_left]

                bytes_left -= len(chunk_data)
                current_part += 1

                try:
                    yield chunk_data
                except (GeneratorExit, asyncio.CancelledError, BrokenPipeError, ConnectionResetError):
                    break

                await asyncio.sleep(0.001)
        except Exception:
            return

    is_stream = request.args.get("st") == "1"
    disposition = "inline" if is_stream else "attachment"

    headers = {
        "Content-Type": worker.mime_type or "video/mp4",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f'{disposition}; filename="{worker.name}"',
        "Access-Control-Allow-Origin": "*",
    }

    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        return Response(media_streamer(), status=206, headers=headers)
    
    return Response(media_streamer(), status=200, headers=headers)

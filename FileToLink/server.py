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


@app.route('/dl/<int:archive_id>/<path:name>', methods=['GET', 'HEAD'])
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

    if not message or not file_size or file_size == 0:
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
    start = 0
    end = file_size - 1

    if range_header:
        try:
            ranges = range_header.replace("bytes=", "").split("-")
            start = int(ranges[0]) if ranges[0] else 0
            if len(ranges) > 1 and ranges[1]:
                end = int(ranges[1])
        except ValueError:
            start = 0
            end = file_size - 1

    if start >= file_size:
        return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    end = min(end, file_size - 1)
    content_length = (end - start) + 1

    is_stream = request.args.get("st") == "1"
    disposition_type = "inline" if is_stream else "attachment"

    headers = {
        "Content-Type": worker.mime_type or "video/mp4",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f'{disposition_type}; filename="{worker.name}"',
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Content-Type, Origin",
    }

    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        status = 206
    else:
        status = 200

    # HEAD request me body bhejne par Hypercorn hang hota hai
    if request.method == "HEAD":
        return Response(b"", status=status, headers=headers)

    async def media_streamer():
        # Pyrogram default block/part is calculated per 1MB chunk offset
        part_size = 1024 * 1024
        first_part = math.floor(start / part_size)
        offset = start % part_size
        bytes_remaining = content_length

        try:
            async for chunk in bot.stream_media(message, offset=first_part):
                if bytes_remaining <= 0:
                    break

                if offset > 0:
                    if len(chunk) <= offset:
                        offset -= len(chunk)
                        continue
                    else:
                        chunk = chunk[offset:]
                        offset = 0

                if len(chunk) > bytes_remaining:
                    chunk = chunk[:bytes_remaining]

                bytes_remaining -= len(chunk)
                yield chunk
                await asyncio.sleep(0)
        except (asyncio.CancelledError, GeneratorExit, BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            pass

    return Response(media_streamer(), status=status, headers=headers)

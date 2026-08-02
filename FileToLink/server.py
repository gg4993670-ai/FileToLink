from asyncio import get_event_loop
from urllib.parse import unquote
import os
import gc

from pyrogram.errors import MessageIdInvalid
from quart import Quart, abort, request, Response, redirect

from FileToLink import Config
from FileToLink.worker import Worker, create_worker, AllWorkers, NotFound


loop = get_event_loop()
app = Quart("FileToLink-Bot")


@app.route('/')
async def root():
    return redirect("https://t.me/shadow_bots")


@app.route('/dl/<int:archive_id>/<name>')
async def download(archive_id: int, name: str):
    worker: Worker = AllWorkers.get(archive_id=archive_id)
    if worker is None:
        try:
            worker = await create_worker(archive_id)
        except (ValueError, MessageIdInvalid):
            NotFound.append(archive_id)
            return abort(404)

    name = unquote(name)
    if name != worker.name or not os.path.isfile(worker.path):
        return abort(404)

    file_size = worker.size

    if not worker.parts[0]:
        await worker.first_dl()

    range_header = request.headers.get("Range")
    start = 0
    end = file_size - 1

    if range_header:
        ranges = range_header.replace("bytes=", "").split("-")
        start = int(ranges[0]) if ranges[0] else 0
        if len(ranges) > 1 and ranges[1]:
            end = int(ranges[1])

    end = min(end, file_size - 1)
    content_length = (end - start) + 1

    async def file_stream():
        current_byte = start
        try:
            with open(worker.path, "rb") as f:
                f.seek(start)
                while current_byte <= end:
                    part_number = worker.worker.part_number(current_byte + 1) if hasattr(worker, 'worker') else worker.part_number(current_byte + 1)
                    if not worker.parts[part_number]:
                        await worker.dl(part_number)

                    loop.create_task(worker.pre_dl(part_number))

                    # RAM bachane ke liye chota chunk size (2KB) use kiya hai
                    chunk_size = min(2048, (end - current_byte) + 1)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    current_byte += len(chunk)
                    yield chunk
                    gc.collect() # Force memory cleanup
        except (BrokenPipeError, ConnectionResetError):
            pass

    headers = {
        "Content-Type": worker.mime_type or "application/octet-stream",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f'{"inline" if request.args.get("st") else "attachment"}; filename="{worker.name}"',
    }

    status_code = 206 if range_header else 200
    return Response(file_stream(), status=status_code, headers=headers)

from asyncio import get_event_loop
from urllib.parse import unquote
import os

from pyrogram.errors import MessageIdInvalid
from quart import Quart, abort, request, send_file, redirect

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

    # Make sure initial bytes exist before sending headers
    if not worker.parts[0]:
        await worker.first_dl()

    # Direct built-in Quart send_file (Handles Range Requests, Sockets & Buffering natively)
    return await send_file(
        worker.path,
        mimetype=worker.mime_type or "video/mp4",
        as_attachment=not bool(request.args.get('st')),
        attachment_filename=worker.name,
        conditional=True
    )

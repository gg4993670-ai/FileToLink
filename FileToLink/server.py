from asyncio import get_event_loop
from urllib.parse import unquote
import os

from pyrogram.errors import MessageIdInvalid
from quart import Quart, abort, request, send_file, redirect
from quart.wrappers.response import FileBody as Fb

from FileToLink import Config
from FileToLink.worker import Worker, create_worker, AllWorkers, NotFound


loop = get_event_loop()

app = Quart("FileToLink-Bot")


class FileBody(Fb):
    def __init__(self, file_path, *, buffer_size=None):
        super(FileBody, self).__init__(file_path, buffer_size=buffer_size)
        file_id = str(self.file_path.resolve()).split('/')[-2]
        self.worker: Worker = AllWorkers.get(file_id=file_id)
        self.current_part: int = 0
        self.last_read_byte: int = 0

    async def __anext__(self) -> bytes:
        current = await self.file.tell()
        if current >= self.end:
            raise StopAsyncIteration()
        read_size = min(self.buffer_size, self.end - current)
        
        # Part ko download hone do read karne se pehle
        part_number = self.worker.part_number(current + 1)
        if not self.worker.parts[part_number]:
            await self.worker.dl(part_number)
            
        loop.create_task(self.worker.pre_dl(part_number))

        chunk = await self.file.read(read_size)
        if chunk:
            return chunk
        else:
            raise StopAsyncIteration()


app.response_class.file_body_class = FileBody


@app.route('/')
async def root():
    return redirect(f"https://t.me/shadow_bots")


@app.route('/dl/<int:archive_id>/<name>')
async def download(archive_id: int, name: str):
    worker: Worker = AllWorkers.get(archive_id=archive_id)
    if worker is None:
        try:
            worker: Worker = await create_worker(archive_id)
        except (ValueError, MessageIdInvalid):
            NotFound.append(archive_id)
            return abort(404)

    name = unquote(name)
    if name != worker.name or not os.path.isfile(worker.path):
        return abort(404)

    # First part readiness check
    if not worker.parts[0]:
        await worker.first_dl()

    response = await send_file(worker.path, mimetype=worker.mime_type,
                               as_attachment=not bool(request.args.get('st')),
                               attachment_filename=worker.name)
    
    # EXACT FIX HERE: 'Config.Part_size' ki jagah 'accept_ranges="bytes"' pass kiya hai
    if request.range is not None and len(request.range.ranges) > 0:
        await response.make_conditional(request, accept_ranges="bytes")

    return response

import serial
import inspect
import json
import asyncio
from typing import Any, Callable, Awaitable

Handler = Callable[[dict[str, Any]], None | Awaitable[None]]
__HANDLERS: dict[str, Handler] = {}

# The internal stack to queue packages that need to be sent to the esp32
__send_queue: asyncio.Queue[bytes] = asyncio.Queue()


def register_handler(packet_type: str, handler: Handler):
    print(f"Registered handler for packet type: {packet_type}")
    __HANDLERS[packet_type] = handler


async def _handle_receive(text: str):
    try:
        payload: dict[str, Any] = json.loads(text)
    except ValueError as e:
        print(e)
        return

    packet_id = payload.get("packet_id", None)
    packet_type = payload.get("packet_type", None)

    print(f"Received packet of type {packet_type} with id {packet_id}")

    if not packet_type or not packet_id:
        return

    await _call_correct_handler(packet_type, payload)


async def _call_correct_handler(packet_type: str, payload: dict[str, Any]):
    handler = __HANDLERS.get(packet_type, None)
    if not handler:
        return
    result = handler(payload)
    if inspect.isawaitable(result):
        await result


async def _handle_line(line: bytes):
    if not line: return
    text = line.decode(errors="replace").strip()
    if not text: return
    await _handle_receive(text)


def write_serial(payload: dict):
    """Writes a packet of data to serial (to be recieved by the esp32)

    Args:
        payload (dict): _description_
    """
    data = json.dumps(payload)
    sendoff = data + "\n"
    print(f"Queueing {data}")
    __send_queue.put_nowait(sendoff.encode())


async def _read_loop(s: serial.Serial):
    while True:
        line = await asyncio.to_thread(s.readline)
        if not line:
            continue
        print(f"Received: {line!r}")
        await _handle_line(line)


async def _write_loop(s: serial.Serial):
    while True:
        packet = await __send_queue.get()
        print(f"Sending: {packet.decode(errors="replace").strip()}")
        await asyncio.to_thread(s.write, packet)
        __send_queue.task_done()

async def run_serial(serial_url: str = "rfc2217://localhost:4000"):
    print(f"Connecting to {serial_url}")
    s = await asyncio.to_thread(serial.serial_for_url, serial_url, timeout=.1)

    read_task = asyncio.create_task(_read_loop(s))
    write_task = asyncio.create_task(_write_loop(s))

    try:
        await asyncio.gather(read_task, write_task)
    except asyncio.CancelledError:
        pass
    finally:
        read_task.cancel()
        write_task.cancel()
        await asyncio.gather(read_task, write_task, return_exceptions=True)
        await asyncio.to_thread(s.close)
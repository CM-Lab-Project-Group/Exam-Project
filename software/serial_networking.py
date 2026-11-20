import serial
import json
import asyncio
from typing import Any, Callable, Awaitable

Handler = Callable[[dict], None]
__HANDLERS: dict[str, Handler] = {}

# The internal stack to queue packages that need to be sent to the esp32
__sendoff_stack: list[bytes] = []


def register_handler(packet_type: str, handler: Handler):
    __HANDLERS[packet_type] = handler


def _handle_receive(text: str):
    try:
        payload: dict[str, Any] = json.loads(text)
    except ValueError as e:
        return

    packet_id = payload.get("packet_id", None)
    packet_type = payload.get("packet_type", None)

    if not packet_type or not packet_id:
        return

    _call_correct_handler(packet_type, payload)


def _call_correct_handler(packet_type: str, payload: dict[str, Any]):
    handler = __HANDLERS.get(packet_type, None)
    if not handler:
        return
    return handler(payload)


def _handle_line(line: bytes):
    if not line: return
    text = line.decode().strip()
    if not text: return
    _handle_receive(text)


def write_serial(payload: dict):
    """Writes a packet of data to serial (to be recieved by the esp32)

    Args:
        payload (dict): _description_
    """
    data = json.dumps(payload) + "\n"
    __sendoff_stack.append(data.encode())


def _read_serial(s: serial.Serial):
    line = s.readline()
    _handle_line(line)


def _dump_waiting_packets(s: serial.Serial):
    while len(__sendoff_stack) > 0:
        s.write(__sendoff_stack.pop())

def poll_serial(serial_url: str = "rfc2217://localhost:4000"):
    with serial.serial_for_url(url=serial_url) as s:
        _read_serial(s)
        _dump_waiting_packets(s)
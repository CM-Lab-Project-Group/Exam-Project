import json
import sys
import asyncio
from asyncio import StreamReader

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Callable, Awaitable
    Handler = Callable[[dict], Awaitable[dict | None]]

__HANDLERS: dict[str, "Handler"] = {}

def error_packet(error_message: str):
    return json.dumps({
        "packet_type": "error",
        "error": error_message,
        "packet_id": -10,
    });


async def listenForIncomingPackets():
    reader: StreamReader = asyncio.StreamReader(sys.stdin)
    while True:
        json_input: dict = await __read_json(reader)

        packet_id = json_input.get("packet_id", None)
        packet_type = json_input.get("packet_type", None)

        if not packet_id or not packet_type:
            print(error_packet("Invalid Packet (no packet_id or packet_type)"))
            continue

        handler_result: dict | None = await __run_correct_handler(
            payload=json_input,
            packet_type=packet_type
        )

        if not handler_result:
            print(error_packet("No handler result!"))
            continue

        if not handler_result.get("packet_id", None) == None:  # <= This is to avoid overriding intenionally set packet_ids
            handler_result["packet_id"] = packet_type

        print(json.dumps(handler_result))


async def __read_json(reader: asyncio.StreamReader) -> dict:
    """Reads data from a stream reader

    Args:
        reader (asyncio.StreamReader): The reader where the json should be read from

    Returns:
        dict: The json as a dictionary. This is empty when there was an error during parsing
    """
    input_bytes = await reader.readline()
    input_str = input_bytes.decode().strip()

    try:
        json_input = json.loads(input_str)
    except ValueError:
        print(json.dumps({
            "error": "Invalid JSON"
        }))
        return {}

    if not isinstance(json_input, dict):
        print(json.dumps({
            "error": "Invalid Packet"
        }))
        return {}
    
    return json_input


async def __run_correct_handler(payload: dict, packet_type: str):
    handler = __HANDLERS.get(packet_type, None)
    if handler is None:
        return None
    return await handler(payload)


def register_handler(packet_type: str, handler: "Handler"):
    """Registers a callback handler for incoming packets
    
    Note:
        If more than one handler is registered for a packet type, only the last one is executed. See hardware.py for usage example

    Args:
        packet_type (str): The packet_type for which the handler should be executed
        handler (Handler): The callback which should be executed
    """
    __HANDLERS[packet_type] = handler

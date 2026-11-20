import json
import sys
import asyncio
from typing import Callable, Awaitable

Handler = Callable[[dict], Awaitable[dict | None]]
__HANDLERS: dict[str, Handler] = {}


async def listenForIncomingPackets():
    reader = asyncio.StreamReader(sys.stdin)
    while True:
        input_bytes = await reader.readline()
        input_str = input_bytes.decode().strip()

        try:
            json_input = json.loads(input_str)
        except ValueError:
            print(json.dumps({
                "error": "Invalid JSON"
            }))
            continue

        if not isinstance(json_input, dict):
            print(json.dumps({
                "error": "Invalid Packet"
            }))
            continue

        packet_id = json_input.pop("packet_id", None)
        packet_type = json_input.pop("packet_type", None)

        if not packet_id or not packet_type:
            print(json.dumps({
                "error": "Invalid Packet (no packet_id or packet_type)"
            }))
            continue

        handler_result = await __run_correct_handler(json_input, packet_type=packet_type)
        
        if not handler_result:
            continue
        
        if not handler_result.get("packet_id", None) == None:
            handler_result["packet_id"] = packet_type

        print(json.dumps(handler_result))


async def __run_correct_handler(payload: dict, packet_type: str):
    handler = __HANDLERS.get(packet_type, None)
    if handler is None:
        return None
    return await handler(payload)


async def register_handler(packet_type: str, handler: Handler):
    """Registers a callback handler for incoming packets
    
    Note:
        If more than one handler is registered for a packet type, only the last one is executed

    Args:
        packet_type (str): The packet_type for which the handler should be executed
        handler (Handler): The callback which should be executed
    """
    __HANDLERS[packet_type] = handler

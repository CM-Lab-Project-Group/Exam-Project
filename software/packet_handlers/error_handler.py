from typing import Any
from serial_networking import register_handler

def register():
    register_handler("error", __handle_error_packet)

async def __handle_error_packet(payload: dict[str, Any]):
    print(f"Hardware-side error: {payload.get("error", "")}")
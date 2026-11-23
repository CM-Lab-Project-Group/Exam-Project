from typing import Any

from serial_networking import register_handler

def register():
    register_handler("ack", __ack_packet_handler)

def __ack_packet_handler(data: dict[str, Any]):
    print(f"Hardware acknowledged packet with id {data.get("packet_id", 0)}")

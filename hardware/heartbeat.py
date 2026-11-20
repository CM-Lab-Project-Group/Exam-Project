from networking import register_handler


async def __handle_heartbeat_requrest(data: dict) -> dict:
    return {
        "packet_type": "ack",
        "packet_id": data.get("packet_id", -1)
    }


def register_hearbeat():
    register_handler("heartbeat", __handle_heartbeat_requrest)

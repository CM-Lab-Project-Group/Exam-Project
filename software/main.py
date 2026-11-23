import asyncio
from serial_networking import run_serial, write_serial, register_handler
from packet_handlers import error_handler, ack_handler

async def serial_polling_async_loop():
    await run_serial()

async def main():
    payload = {
        "packet_type": "heartbeat"
    }

    error_handler.register()
    ack_handler.register()

    write_serial(payload)

    await serial_polling_async_loop()

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
from serial_networking import poll_serial

async def serial_polling_async_loop(loop: asyncio.AbstractEventLoop):
    while True: await loop.run_in_executor(None, poll_serial)


async def main():
    loop = asyncio.get_running_loop()

    asyncio.create_task(serial_polling_async_loop(loop))


if __name__ == "__main__":
    asyncio.run(main())
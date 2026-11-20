import asyncio
import networking
import heartbeat


async def main():
    print("Listening")

    heartbeat.register_hearbeat() # registeres the heartbeat handler to be used by networking. Does not block further execution


    asyncio.create_task(networking.listenForIncomingPackets()) # starts coroutine that listens for incoming network messages

    while True:
        await asyncio.sleep(5)

asyncio.run(main())
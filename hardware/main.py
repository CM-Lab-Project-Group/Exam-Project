from time import sleep
import json
import sys
import asyncio

async def receive_data():
    reader = asyncio.StreamReader(sys.stdin)
    while True:
        res = await reader.readline()
        json_data_hopefully = res.decode().strip()
        if not json_data_hopefully:
            print(json.dumps({ "error": "Something is not good" }))
            break
        try:
            payload = json.loads(json_data_hopefully)
        except ValueError:
            print(json.dumps({ "error": "Invalid JSON" }))
            continue
        packet_id = -1

        if ("packet_id" in payload):
            packet_id = payload["packet_id"]

        print(json.dumps({
            "packet_type": 0,
            "packet_id": packet_id
        }))

async def heartbeat():
    counter = 1
    while True:
        # print(f"Hearbeat #{counter}")
        counter += 1
        await asyncio.sleep(5)

async def main():
    print("Listening")

    asyncio.create_task(receive_data())
    asyncio.create_task(heartbeat())

    while True:
        await asyncio.sleep(5)

asyncio.run(main())
import serial
import asyncio
import json

def handle_receive(text: str):
    try:
        payload = json.loads(text)
    except ValueError as e:
        return
    print(payload)

def handle_line(s: serial.Serial, line: bytes):
    if not line: return
    text = line.decode().strip()
    if not text: return
    handle_receive(s, text)


async def read_serial(s: serial.Serial):
    while True:
        line = await asyncio.to_thread(s.readline)
        handle_line(s, line)
        await asyncio.sleep(.01)

async def write_serial(s: serial.Serial, payload: dict):
    data = json.dumps(payload) + "\n"
    s.write(data.encode())

async def main():
    with serial.serial_for_url("rfc2217://localhost:4000") as s:
        reader_task = asyncio.create_task(read_serial(s))

        while True:
            msg = await asyncio.to_thread(input)

            if msg.lower() == ":exit":
                break

            data = json.dumps({
                "packet_id": 5,
                "packet_type": 1,
                "msg": msg
            })

            data = (data + "\n").encode()
            s.write(data)
            print(data)

        reader_task.cancel()

if __name__ == "__main__":
    asyncio.run(main=main())
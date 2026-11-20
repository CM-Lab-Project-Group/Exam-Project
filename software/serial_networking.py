import serial
import json
import asyncio



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
    handle_receive(text)


async def read_serial(s: serial.Serial):
    while True:
        line = await asyncio.to_thread(s.readline)
        handle_line(s, line)
        await asyncio.sleep(.01)

async def write_serial(s: serial.Serial, payload: dict):
    data = json.dumps(payload) + "\n"
    s.write(data.encode())

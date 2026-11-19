from machine import Pin
from time import sleep

led = Pin(13, Pin.OUT)


def start_recording():
    led.on()
    print("Recording started")


def stop_recording():
    led.off()
    print("Recording stopped")


# Test: pretend the camera records for 3 seconds, every 6 seconds
while True:
    start_recording()
    sleep(3)
    stop_recording()
    sleep(3)

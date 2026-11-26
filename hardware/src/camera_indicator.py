from machine import Pin

LED_PIN = 13

_led = None


def setup():
    # Call once at startup in main.py
    global _led
    _led = Pin(LED_PIN, Pin.OUT, value=0)


def start_recording():
    _led.on()


def stop_recording():
    _led.off()
from machine import Pin

# Pins connected to the 74HC595 shift register
data  = Pin(23, Pin.OUT)  # DS
clock = Pin(18, Pin.OUT)  # SHCP
latch = Pin(5, Pin.OUT)   # STCP

def update_leds(level):
    latch.value(0)          # Pause the LEDs while we send new data

    for i in range(8):
        clock.value(0)
        if i < level:
            data.value(1)   # LED ON
        else:
            data.value(0)   # LED OFF
        clock.value(1)      # Push this 1 or 0 into the chip

    latch.value(1)          # Show all 8 LEDs at once

while True:
    text = input()          # Wait for a number (0-8) from the laptop
    if text.isdigit():
        update_leds(int(text))
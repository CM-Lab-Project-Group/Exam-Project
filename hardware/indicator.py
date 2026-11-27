from machine import Pin

# Pins connected to the 74HC595 shift register
data  = Pin(5, Pin.OUT)  # DS
clock = Pin(18, Pin.OUT)  # SHCP
latch = Pin(19, Pin.OUT)   # STCP

def update_leds(level):
    """Light up `level` LEDs (0 to 8) on the 74HC595."""
    level = max(0, min(8, int(level)))
    latch.value(0)

    for i in range(8):
        clock.value(0)
        if i < level:
            data.value(1)
        else:
            data.value(0)
        clock.value(1)

    latch.value(1)

def update_from_rms(rms):
    """Convert RMS volume (0 to 100) to 0-8 LEDs."""
    level = round((rms / 100) * 8)
    update_leds(level)

def update_from_dbfs(dbfs):
    """Convert dBFS volume (-60 to 0) to 0-8 LEDs."""
    level = round(((dbfs + 60) / 60) * 8)
    update_leds(level)
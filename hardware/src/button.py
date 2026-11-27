# Green button on GPIO17, used to start/stop recording manually.
import time
from machine import Pin

BUTTON_PIN = 17
DEBOUNCE_MS = 50    # ignore changes within 50 ms of the last one (bounce)

_button = None
_last_state = 1
_last_change = 0    # when the last real change happened (ms)

def setup():
    ## Call once at startup.
    global _button, _last_state
    _button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
        # Uses the ESP32's internal pull-up resistor (no external resistor needed):
        # the pin reads 1 when the button is not pressed, and 0 when pressed
        # (the button connects Pin17 to ground).
    _last_state = _button.value()

def was_pressed():
    ## True only at the exact moment the button goes down.
    global _last_state, _last_change
    state = _button.value()

    if state == _last_state:
        return False  # nothing changed

    now = time.ticks_ms()
    if time.ticks_diff(now, _last_change) < DEBOUNCE_MS:
        return False  # too soon after the last change: bounce, ignore

    _last_state = state
    _last_change = now

    return state == 0
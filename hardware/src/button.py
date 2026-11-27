# Green button on GPIO17, used to start/stop recording manually.
from machine import Pin

BUTTON_PIN = 17

_button = None
_last_state = 1     # state from the last check (1 = not pressed)


def setup():
    ## Call once at startup.
    global _button, _last_state
    _button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
        # Uses the ESP32's internal pull-up resistor (no external resistor needed):
        # the pin reads 1 when the button is not pressed, and 0 when pressed
        # (the button connects Pin17 to ground).
    _last_state = _button.value()


def was_pressed():
    global _last_state
    state = _button.value()

    if state == _last_state:
        return False  # nothing changed

    _last_state = state
    return state == 0  # True if it just went down (pressed), False if released
# Buzzer on Pin 25 of esp1:
#   beep_start() -> short high beep (recording started)
#   beep_stop()  -> longer low beep (recording stopped)
#
# Doesn't use sleep(): a beep is switched on, and update() switches it off
# once its time is up. main.py calls update() on every pass of its main loop.

import time
from machine import Pin, PWM

BUZZER_PIN = 25
DUTY_ON = 32768  # 50% = sound on (range 0-65535)

_pwm = None
_beep_end = None  # when the current beep should stop (ms), None = silent


def setup():
    ## Call once at startup.
    global _pwm
    _pwm = PWM(Pin(BUZZER_PIN))
    _pwm.duty_u16(0)  # start silent


def beep(freq, duration_ms):
    ## Start a beep and return immediately.
    global _beep_end
    _pwm.freq(freq)
    _pwm.duty_u16(DUTY_ON)
    _beep_end = time.ticks_add(time.ticks_ms(), duration_ms)


def beep_start():
    beep(2000, 150)   # short high beep


def beep_stop():
    beep(1000, 400)   # longer low beep


def stop():
    ## Silence the buzzer immediately (emergency state from protocol).
    global _beep_end
    _pwm.duty_u16(0)
    _beep_end = None


def update():
    ## Call on every pass of the main loop. Turns the beep off when its time is up.
    if _beep_end is not None and time.ticks_diff(time.ticks_ms(), _beep_end) >= 0:
        stop()
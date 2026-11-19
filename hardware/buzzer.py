from machine import Pin, PWM
from time import sleep

buzzer = PWM(Pin(25))
buzzer.duty_u16(0)  # start silent


def beep(freq, seconds):
    buzzer.freq(freq)        # pitch in Hz (higher number = higher sound)
    buzzer.duty_u16(32768)   # sound on
    sleep(seconds)
    buzzer.duty_u16(0)       # sound off


def beep_start():
    beep(2000, 0.15)         # one short high beep
    print("Beep: recording started")


def beep_stop():
    beep(1000, 0.1)          # two low beeps
    sleep(0.1)
    beep(1000, 0.1)
    print("Beep: recording stopped")


# Test: start beep, wait 3 s, stop beep, wait 3 s, repeat
while True:
    beep_start()
    sleep(3)
    beep_stop()
    sleep(3)

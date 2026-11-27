# Test for button.py (not part of the final program).
# Each press toggles a pretend "recording" on/off and prints it.

import time
import button


def main():
    button.setup()
    recording = False
    print("Press the green button...")

    while True:
        if button.was_pressed():
            recording = not recording
            if recording:
                print("Button pressed -> recording started")
            else:
                print("Button pressed -> recording stopped")

        time.sleep_ms(10)


main()

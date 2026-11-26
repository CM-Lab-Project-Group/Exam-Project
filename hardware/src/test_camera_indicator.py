# Test for camera_indicator.py (not part of the final program).
# Turns the LED on for 3 s and off for 3 s, forever.

import time
import camera_indicator


def main():
    camera_indicator.setup()
    while True:
        print("Recording started")
        camera_indicator.start_recording()
        time.sleep(3)
        print("Recording stopped")
        camera_indicator.stop_recording()
        time.sleep(3)


main()

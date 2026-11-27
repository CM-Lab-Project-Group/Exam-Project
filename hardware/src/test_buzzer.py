# Test for buzzer.py (not part of the final program).
# Shows the "one main loop" style
# it just keeps calling buzzer.update().

import time
import buzzer


def main():
    buzzer.setup()
    last_change = time.ticks_ms()
    recording = False

    while True:
        # every 3 seconds, pretend recording starts or stops
        if time.ticks_diff(time.ticks_ms(), last_change) >= 3000:
            last_change = time.ticks_ms()
            recording = not recording
            if recording:
                print("Recording started")
                buzzer.beep_start()
            else:
                print("Recording stopped")
                buzzer.beep_stop()

        buzzer.update()
        time.sleep_ms(10)


main()

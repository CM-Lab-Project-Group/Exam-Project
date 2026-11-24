import sounddevice as sd
import numpy as np
import time

# Variable to share the volume between the microphone and the screen
current_volume = 0

# 1. Measure the microphone loudness in the background
def check_sound(indata, frames, time_info, status):
    global current_volume
    
    # Calculate the true average loudness (a decimal between 0.0 and 1.0)
    rms = np.sqrt(np.mean(indata**2))
    
    # Convert to a 0-100 scale (change 300 if your mic is too quiet or too loud)
    volume = int(rms * 300)
    
    # Cap the volume at 100 maximum
    current_volume = min(volume, 100)

# 2. Start listening and update the bar smoothly
print("Listening... Make some noise! (Press Ctrl+C to stop)")

try:
    with sd.InputStream(callback=check_sound):
        while True:
            # Create a 50-block horizontal bar
            bar_length = current_volume // 2
            bar = "█" * bar_length + "-" * (50 - bar_length)
            
            # Print the volume and bar on the same line
            print(f"\rVolume: {current_volume:3d}/100 |{bar}|", end="", flush=True)
            
            # Update the screen 20 times per second
            time.sleep(0.05)
except KeyboardInterrupt:
    print("\nStopped.")
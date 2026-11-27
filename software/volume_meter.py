import sounddevice as sd
import numpy as np
import serial

# Connect to the Wokwi ESP32
ser = serial.serial_for_url("rfc2217://localhost:4000", baudrate=115200)

# Start listening to the laptop microphone
mic = sd.InputStream(channels=1, samplerate=16000)
mic.start()

print("Listening... Press Ctrl+C to stop.")

while True:
    audio, _ = mic.read(1024)         # Grab a small chunk of audio
    loudness = np.abs(audio).mean()   # Get the average volume
    level = int(loudness * 100)       # Scale it up (adjust 100 if needed)
    level = min(8, level)             # Never go above 8 LEDs

    ser.write(f"{level}\n".encode())  # Send the number to the ESP32
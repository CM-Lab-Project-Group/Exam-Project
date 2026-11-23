from machine import Pin, ADC, I2C
import ssd1306
import time

# 1. Set up the microphone on Pin 34
mic = ADC(Pin(34))
# Allow the pin to read the full 0V to 3.3V range
mic.atten(ADC.ATTN_11DB)

# 2. Set up the OLED screen on Pins 21 (SDA) and 22 (SCL)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
# Create a screen object that is 128 pixels wide and 64 pixels tall
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

while True:
    # 3. Measure sound wave height by taking 50 quick readings
    lowest = 4095
    highest = 0
    
    for i in range(50):
        val = mic.read()
        if val > highest:
            highest = val
        if val < lowest:
            lowest = val
            
    # The loudness is the difference between the highest and lowest wave points
    loudness = highest - lowest

    # 4. Turn that raw reading into a simple volume score from 0 to 100
    # (Change 2000 to a smaller number if your mic isn't sensitive enough)
    volume = int((loudness * 100) / 2000)
    
    # Keep the volume number capped at 100 maximum
    if volume > 100:
        volume = 100

    # 5. Update the OLED screen
    oled.fill(0) # Clear the screen to black
    
    # Draw the text showing the volume from 0 to 100
    oled.text("Volume: " + str(volume), 0, 10)
    
    # Draw the outer empty box for the volume bar (104 pixels wide, 16 pixels tall)
    oled.rect(0, 35, 104, 16, 1)
    
    # Fill the inside of the bar based on the volume (0 to 100 pixels wide)
    oled.fill_rect(2, 37, volume, 12, 1)
    
    # Push everything to the screen so we can see it
    oled.show()
    
    # Wait a tiny fraction of a second before updating again
    time.sleep(0.05)
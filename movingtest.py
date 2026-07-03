import time

from lib.lights import moving_heads

try:
    while True:
        for i in range(256):
            for head in moving_heads:
                head.setLight(i, 255 - i, 0, 0, 50)
                head.setDir(i, 100)
            time.sleep(0.05)

        for i in range(256):
            for head in moving_heads:
                head.setLight(255 - i, i, 0, 0, 50)
                head.setDir(255 - i, 100)
            time.sleep(0.05)

except KeyboardInterrupt:
    print("\nTerminating stream...")

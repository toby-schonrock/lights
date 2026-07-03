import time
import math

from lib.lights import panels

state = 255
while True:
    for i in range(360):
        for panel in panels:
            r = (math.sin(math.radians(i + panel.channel * 3)) + 1) / 2
            g = (math.sin(math.radians(i + 120 + panel.channel * 3)) + 1) / 2
            b = (math.sin(math.radians(i + 240 + panel.channel * 3)) + 1) / 2
            panel.setLight(r * 255, g * 255, b * 255)
        time.sleep(0.025)

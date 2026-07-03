import random
import time

from lib.lights import panels, send_dmx

panel = panels.a
for i in range(10):
    panel.setLight(0, 0, 0)
    panel = random.choice(panels)
    panel.setLight(0, 255, 0)
    time.sleep(4/(11-i) + 0.1)

send_dmx()

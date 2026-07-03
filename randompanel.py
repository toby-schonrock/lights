import random
import time

from lib.lights import panels, send_dmx

panel = panels.a
for i in range(15):
    panel.setLight(0, 0, 0)
    panel = random.choice(panels)
    panel.setLight(0, 255, 0)
    time.sleep(3/(15-i) + 0.1)

send_dmx()

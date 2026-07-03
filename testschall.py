import time

from lib.lights import panels

state = 255
while True:
    panels.a.setLight(255 - state, state, 0)
    state = 255 - state
    time.sleep(0.5)

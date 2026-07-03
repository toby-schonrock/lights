import time

from lib.lights import moving_heads, overheads, send_dmx, reset

for head in moving_heads:
    angle_offset = (head.channel - 401) / 14
    # print(angle_offset)
    head.setDir(29 + angle_offset * 3, 17)

time.sleep(3)

for head in moving_heads:
    head.setLight(255, 255, 255, 255, 255, 255)

for head in overheads:
    head.setLight(255, 255, 255, 255, 255)

time.sleep(3)
reset()
send_dmx()

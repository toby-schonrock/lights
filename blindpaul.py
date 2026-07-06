import time

import lib.arion_lights as light
import lib.artnetcontroller as anc

controller = anc.ArtNetController("192.168.1.169")

for head in light.moving_heads:
    angle_offset = (head.channel - 401) / 14
    head.setDir(29 + angle_offset * 3, 17)

controller.send_packet(light.get_channel_values())
time.sleep(3)

for head in light.moving_heads:
    head.setLight(255, 255, 255, 255, 255, 255)

for head in light.overheads:
    head.setLight(255, 255, 255, 255, 255)

controller.send_packet(light.get_channel_values())
time.sleep(3)

light.reset()
controller.send_packet(light.get_channel_values())

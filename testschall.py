import time
import math

import lib.arion_lights as light
import lib.artnetcontroller as anc

controller = anc.ArtNetController("192.168.1.169")
threadkill = light.spawn_update_thread(controller.send_packet)

for _ in range(10):
    light.panels.a.g = 255
    time.sleep(0.5)
    light.panels.a.g = 0
    time.sleep(0.5)


threadkill()

while True:
    for i in range(360):
        for panel in light.panels:
            r = (math.sin(math.radians(i + panel.channel * 3)) + 1) / 2
            g = (math.sin(math.radians(i + 120 + panel.channel * 3)) + 1) / 2
            b = (math.sin(math.radians(i + 240 + panel.channel * 3)) + 1) / 2
            panel.setLight(r * 255, g * 255, b * 255)
        controller.send_packet(light.get_channel_values())
        time.sleep(0.025)

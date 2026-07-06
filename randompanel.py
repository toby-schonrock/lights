import random
import time

import lib.arion_lights as light
import lib.artnetcontroller as anc

controller = anc.ArtNetController("192.168.1.169")
threadkill = light.spawn_update_thread(controller.send_packet)

panel = light.panels.a
for i in range(15):
    panel.setLight(0, 0, 0)
    panel = random.choice(light.panels)
    panel.setLight(0, 255, 0)
    time.sleep(3/(15-i) + 0.1)

threadkill()
# make sure final frame arrives
time.sleep(0.2)
controller.send_packet(light.get_channel_values())

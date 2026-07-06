import time

import lib.arion_lights as light
import lib.artnetcontroller as anc

controller = anc.ArtNetController("192.168.1.169")

try:
    while True:
        for i in range(256):
            for head in light.moving_heads:
                head.setLight(i, 255 - i, 0, 0, 50)
                head.setDir(i, 100)
            time.sleep(0.05)
            controller.send_packet(light.get_channel_values())

        for i in range(256):
            for head in light.moving_heads:
                head.setLight(255 - i, i, 0, 0, 50)
                head.setDir(255 - i, 100)
            time.sleep(0.05)
            controller.send_packet(light.get_channel_values())

except KeyboardInterrupt:
    print("\nTerminating stream...")

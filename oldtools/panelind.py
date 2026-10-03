from lib.scenes import Scene, SceneScript

import time

from lib.artnetcontroller import ArtNetController

controller = ArtNetController("192.168.1.169")

class ind(SceneScript):
    def run(self):
        lights = self.lights
        for panel in lights.panels:
            lights.panels.reset()
            panel.setLight(255,255,0)
            time.sleep(1)

scene = Scene(ind(), [], lambda lights: controller.send_packet(lights.get_channel_values()))
time.sleep(3)

scene.start()

input()
from examples import ArionScene, PanelWave
from lib.arion_lights import LightConfig
from lib.scenes import SceneConfig, Scene

from lib.arion_lights import LightState

from lib.artnetcontroller import ArtNetController
controller = ArtNetController("192.168.1.169")
callback = lambda lights: controller.send_packet(lights.get_channel_values())

class Kneipe(Scene):
    def on_start(self):
        lights: LightConfig = self.lights
        for panel in lights.panels:
            if panel.position[1] < 1.2:
                panel.setLight(0, 255, 0)
            elif panel.position[1] < 2:
                panel.setLight(255, 255, 255)
            else:
                panel.setLight(0, 0, 255)

        lights.overheads.mid_right.setLight(0, 0, 255, LightState.brightness(255))
        lights.overheads.mid_left.setLight(0, 255, 0, LightState.brightness(255))



scene = Kneipe(SceneConfig.poll(), [PanelWave(2, -45, 0.8, 0.8)])
scene.start()
scene.start_dispatcher(callback)

input()
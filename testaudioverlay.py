import time

import numpy as np

from lib import audio
from lib.arion_lights import LightConfig
from lib.artnetcontroller import ArtNetController
from lib.scenes import AudioOverlay, AudioScene, SceneScript

audio.select_device(True)

controller = ArtNetController("192.168.1.169")

class TestScript(SceneScript):
    def run(self):
        lights = self.lights
        while True:
            for panel in lights.panels:
                panel.setLight(255, 0, 0)
            time.sleep(1)
            for panel in lights.panels:
                panel.setLight(0, 255, 0)
            time.sleep(1)
            for panel in lights.panels:
                panel.setLight(0, 0, 255)
            time.sleep(1)

class TestAudioOverlay(AudioOverlay):
    def apply(self, lights: LightConfig, audio_data: np.ndarray) -> LightConfig:
        # Example: Set all panels brightness based on the average audio amplitude
        avg_amplitude = np.mean(np.abs(audio_data)) * 50 # Scale factor to make it more visible
        for panel in lights.panels:
            panel.r *= avg_amplitude
            panel.g *= avg_amplitude
            panel.b *= avg_amplitude
        return lights

def printargb(lights: LightConfig):
    print(lights.panels.a.r, lights.panels.a.g, lights.panels.a.b)
    return lights

scene = AudioScene(TestScript(), [TestAudioOverlay()], lambda lights: controller.send_packet(lights.get_channel_values()))

scene.start()

input("Press Enter to stop the scene...\n")
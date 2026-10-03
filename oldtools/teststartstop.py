import time

from lib import audio
from lib.scenes import AudioScene, Scene, SceneScript


class TestScript(SceneScript):
    def run(self):
        while True:
            print("Script running")
            time.sleep(1)

scene = Scene(TestScript(), [], lambda _: print("Data sent"), 999)

print("Normal scene")

scene.start()
time.sleep(2)
scene.stop()
time.sleep(2)

print("Audio scene")

audio.select_device(auto=True, print_info=False)

audioscene = AudioScene(TestScript(), [], lambda _: print("Data sent 2"))

audioscene.start()
time.sleep(0.1)
audioscene.stop()
input()
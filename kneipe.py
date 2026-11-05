from examples import PanelWave, arion_panels
from lib.artnetcontroller import ArtNetController
from lib.scenes import Scene, SceneConfig

controller = ArtNetController("192.168.1.169")
callback = lambda lights: controller.send_packet(lights.get_channel_values())

scene = Scene(
    SceneConfig.poll(), background=arion_panels(), layers=[PanelWave(2, -45, 0.8, 0.8)]
)
scene.start_dispatcher(callback)

input()
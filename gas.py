# For end to end testing

# !!!!!!! WARNING !!!!!!!
# Letting this run for extended periods 
# of time can lead to alchohol poisoning.

# Use at own risk

from examples import RainbowsPanel
from lib import audio
from lib.artnetcontroller import ArtNetController
from lib.scenes import AudioScene
from visualiser import VisualiserDimmerOverlay

audio.select_device(True)

controller = ArtNetController("192.168.1.169")

scene = AudioScene(RainbowsPanel(), [VisualiserDimmerOverlay()], lambda lights: controller.send_packet(lights.get_channel_values()), True)
scene.start()

input()
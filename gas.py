# For end to end testing

# !!!!!!! WARNING !!!!!!!
# Letting this run for extended periods
# of time can lead to alchohol poisoning.

# Use at own risk

from examples import RainbowsPanel
from lib.scenes import SceneConfig
from lib.virtualrig import VirtualRig
from visualiser import VisualiserDimmerOverlay

rig = VirtualRig()

scene = RainbowsPanel(SceneConfig.playback("audio_files/song.mp3"), [VisualiserDimmerOverlay()])
scene.start()
scene.start_dispatcher(rig.callback)

rig.run()

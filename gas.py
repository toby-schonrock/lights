# !!!!!!! WARNING !!!!!!!
# Letting this run for extended periods of time can lead to alcohol poisoning.
# The creators of this program beer no responsibility for the consequences.

import math
import time
from collections.abc import Callable

import numpy as np

from examples import PanelCircle
from lib.frame_context import FrameContext
from lib.scenes import Overlay, Scene, SceneConfig


class Section:
    def __init__(
        self,
        name: str,
        start: Callable[[Scene], None],
        render: Callable[[Scene], None],
    ):
        self.name = name
        self.start = start
        self.render = render


def gasStart(scene: Scene):
    scene.overlays[0].disabled = False
    scene.overlays[1].disabled = True
    for panel in scene.lights.panels:
        if panel.name >= "m":
            if panel.position[1] < 1.2:
                panel.setLight(255,50,255)
            elif panel.position[1] < 2:
                panel.setLight(255,0,100)
            else:
                panel.setLight(255,0,0)
        else:
            if panel.position[1] < 1.2:
                panel.setLight(100,0,255)
            elif panel.position[1] < 2:
                panel.setLight(50,0,255)
            else:
                panel.setLight(0, 0, 255)

def gasRender(scene: Scene):
    return


gas = Section("gas", gasStart, gasRender)


def normalStart(scene: Scene):
    scene.overlays[0].disabled = True
    scene.overlays[1].disabled = False
    scene.overlays[1].freq = 2.83
    scene.overlays[1].base_mult = 0.5


i = 0


def normalRender(scene: Scene):
    global i
    i = (i + 1) % 360
    # rainbow code
    for panel in scene.lights.panels:
        r = (math.sin(math.radians(i + panel.position[0] * 15)) + 1) / 2
        g = (math.sin(math.radians(i + 120 + panel.position[0] * 15)) + 1) / 2
        b = (math.sin(math.radians(i + 240 + panel.position[0] * 15)) + 1) / 2
        panel.setLight(r * 255, g * 255, b * 255)


normal = Section("normal", normalStart, normalRender)

def pauseStart(scene: Scene):
    scene.overlays[0].disabled = True
    scene.overlays[1].disabled = False
    scene.overlays[1].freq = 0
    scene.overlays[1].base_mult = 0.2

pause = Section("pause", pauseStart, normalRender)

playback = [
    (None, 0.0),
    (gas, 0.4), 
    (normal, 3.2), 
    (pause, 14.4),
    (normal, 19.7), 
    (gas, 28.1),
    (normal, 30.9),
    (pause, 53.4),
    (normal, 56.2),
    (gas, 64.5),
    (normal, 67.4),
    (pause, 78.5),
    (gas, 81.4),
    (normal, 84.2),
    (pause, 95.5),
    (normal, 98.2),
    (gas, 106.6),
    (normal, 109.5),
]

class FlippingHitOverlay(Overlay):
    """
    Set all panels brightness based on the average audio amplitude and flips side past threshold
    """
    def __init__(self, high_mult, base_mult, threshold, flipcooldown = 0.3, disabled = False):
        super().__init__(disabled)
        self.high_mult = high_mult
        self.base_mult = base_mult
        self.threshold = threshold
        self.flipcooldown = flipcooldown
        
        self.side = "Right"
        self.lastflip = -flipcooldown
        self.dropofffreq = 2

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights
        audio_data = context.audio_data
        timestamp = context.timestamp

        if audio_data is None or timestamp is None:
            raise RuntimeError(
                "No audio data availabe. Do you have the correct scene type?"
            )

        time_since = timestamp - self.lastflip
        if time_since >= self.flipcooldown:
            avg_amplitude = np.mean(np.abs(audio_data))
            if avg_amplitude > self.threshold:
                self.side = "Right" if self.side == "Left" else "Left"
                self.lastflip = timestamp
                time_since = 0

        linear = max(1 - (time_since * self.dropofffreq), 0)
        hit = self.base_mult + (self.high_mult - self.base_mult) * linear
        for panel in lights.panels:
            if (panel.name >= "m") == (self.side == "Right"):
                mult = hit
            else:
                mult = self.base_mult
            
            panel.r *= mult
            panel.g *= mult
            panel.b *= mult
                

        return context

class Gas(Scene):
    def __init__(self, config, overlays=None):
        super().__init__(config, overlays)
        self.sectionIdx: int = 0

    def check_transitions(self):
        if self.context is None:
            return

        timestamp = self.context.timestamp
        if timestamp is None:
            raise RuntimeError("Timestamp not available! Worng scene type?")

        next = self.sectionIdx + 1
        if next == len(playback) and timestamp < playback[self.sectionIdx]:
            self.sectionIdx = 0
        elif next != len(playback) and playback[next][1] < timestamp:
            self.sectionIdx = next
            print("Started section:", playback[self.sectionIdx][0].name)
            playback[self.sectionIdx][0].start(self)

    def run(self):
        while True:
            self.check_transitions()
            secton = playback[self.sectionIdx][0]
            if secton:
                secton.render(self)
            
            time.sleep(0.020)


# from lib.virtualrig import VirtualRig
# rig = VirtualRig()
# callback = rig.callback

from lib.artnetcontroller import ArtNetController

controller = ArtNetController("192.168.1.169")
callback = lambda lights: controller.send_packet(lights.get_channel_values())

circle = PanelCircle(2.83, 0.5)

scene = Gas(
    SceneConfig.playback("audio_files/song.mp3"),
    [FlippingHitOverlay(1, 0.2, 0.2), circle], 
)
scene.start()
scene.start_dispatcher(callback)

input()
# rig.run()
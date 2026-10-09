# For end to end testing

# !!!!!!! WARNING !!!!!!!
# Letting this run for extended periods
# of time can lead to alchohol poisoning.

# Use at own risk

import math
import time
from collections.abc import Callable

from examples import PanelCircle, VolumeDimmer
from lib.scenes import Scene, SceneConfig


class Section:
    def __init__(
        self,
        name: str,
        startTimes: list[float],
        start: Callable[[Scene], None],
        render: Callable[[Scene], None],
    ):
        self.name = name
        self.startTimes = startTimes
        self.start = start
        self.render = render


def gasStart(scene: Scene):
    scene.overlays[0].disabled = False
    scene.overlays[1].disabled = True

    for panel in scene.lights.panels:
        if panel.position[1] < 1.2:
            panel.setLight(0, 255, 0)
        elif panel.position[1] < 2:
            panel.setLight(255, 255, 255)
        else:
            panel.setLight(0, 0, 255)


def gasRender(scene: Scene):
    return


gas = Section("gas", [0, 28.1, 64.5, 106.6], gasStart, gasRender)


def normalStart(scene: Scene):
    scene.overlays[0].disabled = True
    scene.overlays[1].disabled = False


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


normal = Section("normal", [3.2, 30.9, 67.4, 109.5], normalStart, normalRender)

sections = [gas, normal]


class Gas(Scene):
    def __init__(self, config, overlays=None):
        super().__init__(config, overlays)
        self.currentSection: Section | None = None

    def getSection(self, timestamp):
        lastStartTimes = [
            next((x for x in reversed(section.startTimes) if x <= timestamp), -1)
            for section in sections
        ]
        sectionIdx = lastStartTimes.index(max(lastStartTimes))
        return sections[sectionIdx]

    def check_transitions(self):
        if self.context is None:
            return

        timestamp = self.context.timestamp
        if timestamp is None:
            raise RuntimeError("Timestamp not available! Worng scene type?")

        section = self.getSection(timestamp)
        if section != self.currentSection:
            print("Started section:", section.name)
            self.currentSection = section
            section.start(self)

    def run(self):
        while True:
            self.check_transitions()
            if self.currentSection:
                self.currentSection.render(self)
            
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
    [VolumeDimmer(), circle],
)
scene.start()
scene.start_dispatcher(callback)

input()
# rig.run()
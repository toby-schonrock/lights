# For end to end testing

# !!!!!!! WARNING !!!!!!!
# Letting this run for extended periods
# of time can lead to alchohol poisoning.

# Use at own risk

import math
import time

from examples import VolumeDimmer
from lib.scenes import Scene, SceneConfig
from lib.virtualrig import VirtualRig
from visualiser import VisualiserDimmerOverlay

rig = VirtualRig()


class Section:
    def __init__(self, name: str, startTimes: list[float]):
        self.name = name
        self.startTimes = startTimes


gas = Section("gas", [0, 28.1, 64.5, 106.6])
normal = Section("normal", [3.2, 30.9, 67.4, 109.5])
sections = [gas, normal]


class Gas(Scene):
    def __init__(self, config, overlays=None):
        super().__init__(config, overlays)
        self.currentSection = None

    def gasSection(self):
        self.overlays[0].disabled = False
        self.overlays[1].disabled = True

    def normalSection(self):
        self.overlays[0].disabled = True
        self.overlays[1].disabled = False

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
            if section == gas:
                self.gasSection()
            elif section == normal:
                self.normalSection()

    def run(self):
        lights = self.lights

        # rainbow code
        while True:
            for i in range(360):
                for panel in lights.panels:
                    r = (math.sin(math.radians(i + panel.position[0] * 15)) + 1) / 2
                    g = (
                        math.sin(math.radians(i + 120 + panel.position[0] * 15)) + 1
                    ) / 2
                    b = (
                        math.sin(math.radians(i + 240 + panel.position[0] * 15)) + 1
                    ) / 2
                    panel.setLight(r * 255, g * 255, b * 255)

                self.check_transitions()
                time.sleep(0.020)


scene = Gas(
    SceneConfig.playback("audio_files/song.mp3"),
    [VolumeDimmer(), VisualiserDimmerOverlay()],
)
scene.start()
scene.start_dispatcher(rig.callback)

rig.run()
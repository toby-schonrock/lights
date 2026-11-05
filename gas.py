# !!!!!!! WARNING !!!!!!!
# Letting this run for extended periods of time can lead to alcohol poisoning.
# The creators of this program beer no responsibility for the consequences.

import numpy as np

from examples import PanelCircle, RainbowPanels
from lib.arion_lights import LightConfig, LightState
from lib.frame_context import FrameContext
from lib.scenes import Layer, Scene, SceneConfig


class FlippingHitOverlay(Layer):
    """
    Set all panels brightness based on the average audio amplitude and flips side past threshold
    """

    def __init__(
        self, high_mult, base_mult, threshold, flipcooldown=0.3, disabled=False
    ):
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

        if timestamp < self.lastflip:
            self.lastflip = -1

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

        for overhead in lights.overheads:
            if overhead.channel < 17:
                mult = hit
            else:
                mult = self.base_mult

            overhead.brightness_strobe = LightState.brightness(mult * 255)

        return context


rainbow_layer = RainbowPanels()
hit_layer = FlippingHitOverlay(1, 0.2, 0.2)
circle_layer = PanelCircle(2.83, 0.5)

layers = [rainbow_layer, circle_layer, hit_layer]


class Section:
    def __init__(
        self,
        name: str,
        layers: list[Layer],
        background: LightConfig,
    ):
        self.name = name
        self.layers = layers
        self.background = background


gas_background = LightConfig()
for panel in gas_background.panels:
    if panel.name >= "m":
        if panel.position[1] < 1.2:
            panel.setLight(255, 50, 255)
        elif panel.position[1] < 2:
            panel.setLight(255, 0, 100)
        else:
            panel.setLight(255, 0, 0)
    else:
        if panel.position[1] < 1.2:
            panel.setLight(100, 0, 255)
        elif panel.position[1] < 2:
            panel.setLight(50, 0, 255)
        else:
            panel.setLight(0, 0, 255)

gas_background.overheads.far_left.setLight(100, 0, 255, LightState.brightness(255))
gas_background.overheads.mid_left.setLight(50, 0, 255, LightState.brightness(255))
gas_background.overheads.mid_right.setLight(255, 0, 100, LightState.brightness(255))
gas_background.overheads.far_right.setLight(255, 50, 255, LightState.brightness(255))


gas = Section("gas", [hit_layer], gas_background)
normal = Section("normal", [RainbowPanels(), PanelCircle(2.8235, 0.5)], LightConfig())
pause = Section("pause", [RainbowPanels(), PanelCircle(0.3529, 0.2)], LightConfig())

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
    (gas, 137.6),
    (normal, 148.7),
]


class SectionedPlayback(Scene):
    def __init__(self, config, section_list: list[tuple[Section | None, float]]):
        super().__init__(config)

        self.section_list = section_list
        self.sectionIdx: int = 0

    def pre_render(self, context: FrameContext) -> FrameContext:
        timestamp = context.timestamp
        if timestamp is None:
            raise RuntimeError("Timestamp not available! Worng scene type?")

        next = self.sectionIdx + 1
        if next == len(self.section_list):  # if at end
            if timestamp < self.section_list[self.sectionIdx][1]:
                # time has gone backwards
                self.sectionIdx = 0
                print("Restarted")

        elif timestamp > self.section_list[next][1]:
            self.sectionIdx = next
            print("Started section:", self.section_list[self.sectionIdx][0].name)
            section = self.section_list[self.sectionIdx][0]
            self.background = section.background
            self.layers = section.layers


from lib.virtualrig import VirtualRig

rig = VirtualRig()
callback = rig.callback

# from lib.artnetcontroller import ArtNetController

# controller = ArtNetController("192.168.1.169")
# callback = lambda lights: controller.send_packet(lights.get_channel_values())

circle = PanelCircle(2.83, 0.5)

scene = SectionedPlayback(SceneConfig.playback("audio_files/song.mp3"), playback)
scene.start_dispatcher(callback)

# input()
rig.run()

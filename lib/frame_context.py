import numpy as np

from lib.arion_lights import LightConfig


class FrameContext:
    def __init__(
        self,
        lights: LightConfig = None,
        audio_data: np.ndarray | None = None,
        timestamp: float | None = None,
    ):
        self.lights = lights
        self.audio_data = audio_data
        self.timestamp = timestamp

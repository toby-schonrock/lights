import numpy as np

from lib.arion_lights import LightConfig


class FrameContext:
    def __init__(
        self,
        lights: LightConfig | None = None,
        audio_data: np.ndarray | None = None,
        timestamp: float | None = None,
        sampling_rate: float | None = None,
    ):
        self.lights = lights
        self.audio_data = audio_data
        self.timestamp = timestamp
        self.sampling_rate = sampling_rate

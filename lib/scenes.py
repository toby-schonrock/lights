from abc import ABC, abstractmethod
from collections.abc import Callable
import sys
import threading
import time
from typing import Union
from copy import deepcopy

import numpy as np
from lib.arion_lights import LightConfig
import lib.audio as audio

class SceneScript(ABC):
    """
    Abstract base class for a background script that sets light values.
    To make a new scene, subclass this and implement the run() method.
    Then build a Scene object with it and start().
    """
    def __init__(self):
        self.lights = LightConfig()

    @abstractmethod
    def run(self):
        """Runs when the scene is active."""
        pass

class Overlay(ABC):
    """Abstract base class for an overlay modifying light values."""
    @abstractmethod
    def apply(self, lights: LightConfig) -> LightConfig:
        pass

class AudioOverlay(ABC):
    """Abstract base class for an overlay modifying light values. Also revieves audio data."""
    @abstractmethod
    def apply(self, lights: LightConfig, audio_data: np.ndarray) -> LightConfig:
        pass

class Scene:
    def __init__(self, bg: SceneScript, overlays: list[Overlay], callback: Callable[[LightConfig], None], ms_interval: float = 25):
        self.bg = bg
        self.overlays = overlays or []
        self.ms_interval = ms_interval
        self.callback = callback

        self._stop_bg_thread = None
        self._stop_dispatcher = None

    def _start_dispatcher(self):
        dp_stop_event = threading.Event()

        def dispatcher_loop():
            interval = self.ms_interval / 1000.0
            next_frame = time.monotonic()

            while not dp_stop_event.is_set():
                current_lights = self._render()
                
                self.callback(current_lights) # todo: pass in callback

                next_frame += interval
                delay = next_frame - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                else:
                    next_frame = time.monotonic()  # System lag recovery

        self._dispatcher = threading.Thread(target=dispatcher_loop, daemon=True)
        self._stop_dispatcher = dp_stop_event.set
        self._dispatcher.start()


    def start(self):
        """Starts both the user's background logic thread and the network dispatcher thread."""
        bg_stop_event = threading.Event()
        
        def run_user_script():
            while not bg_stop_event.is_set():
                self.bg.run()

        self._bg_thread = threading.Thread(target=run_user_script, daemon=True)
        self._stop_bg_thread = bg_stop_event.set
        self._bg_thread.start()

        self._start_dispatcher()


    def _render(self):
        """Renders the current light values without starting any threads."""
        current_lights = deepcopy(self.bg.lights)

        for overlay in self.overlays:
            current_lights = overlay.apply(current_lights)

        return current_lights

    def stop(self):
        """Gracefully halts both background execution and network sending."""
        if self._stop_bg_thread:
            self._stop_bg_thread()
        if self._stop_dispatcher:
            self._stop_dispatcher()
        print("Scene stopped.")

class AudioScene(Scene):
    def __init__(self, bg: SceneScript, overlays: list[Union[Overlay, AudioOverlay]], callback: Callable[[LightConfig], None]):
        super().__init__(bg, overlays, callback)
        self.audio_data = np.zeros(1024)

    def _start_dispatcher(self):
        def handle_audio_data(indata: np.ndarray, frames: int, time, status):
            if status and str(status) == "input overflow":
                print("Input overflow. Could be caused by low latency selected",
                        file=sys.stderr)
                    
            self.audio_data = indata[:, 0]
            lights = self._render(self.audio_data)

            self.callback(lights)

        self._stop_dispatcher = audio.bind(handle_audio_data)

    def _render(self, audio_data: np.ndarray):
        """Renders the current light values without starting any threads."""
        current_lights = deepcopy(self.bg.lights)

        for overlay in self.overlays:
            if isinstance(overlay, AudioOverlay):
                current_lights = overlay.apply(current_lights, audio_data)
            else:
                current_lights = overlay.apply(current_lights)

        return current_lights
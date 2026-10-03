import ctypes
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy

import numpy as np

from lib import audio
from lib.arion_lights import LightConfig


def _force_kill_thread(thread: threading.Thread):
    """
    Forcibly injects a SystemExit exception into a thread to kill it immediately.
    This function is hella bad practice but it is used to allow users to write scene scripts that can be stopped
    without requiring them to implement their own stop logic.
    """
    if not thread or not thread.is_alive():
        return
    
    thread_id = thread.ident
    if thread_id is None:
        return

    # Call CPython's internal API to raise SystemExit in the target thread
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(thread_id), 
        ctypes.py_object(SystemExit)
    )
    
    if res == 0:
        print("Error: Invalid thread ID.")
    elif res > 1:
        # If it affected more than one thread (which shouldn't happen), revert it
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), None)
        print("Error: Failed to safely abort thread cleanly, reverted.")

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
    def __init__(self, script: SceneScript, overlays: list[Overlay], callback: Callable[[LightConfig], None], ms_interval: float = 25):
        self.script = script
        self.overlays = overlays or []
        self.ms_interval = ms_interval
        self.callback = callback

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

        self._dispatcher_thread = threading.Thread(target=dispatcher_loop, daemon=True)
        self._stop_dispatcher = dp_stop_event.set
        self._dispatcher_thread.start()


    def start(self):
        """Starts both the user's background logic thread and the network dispatcher thread."""
        
        def run_user_script():
            try:
                self.script.run()
            except SystemExit:
                # print("Background scene was forcibly terminated.")
                pass
            finally:
                self.stop()

        self._script_thread = threading.Thread(target=run_user_script, daemon=True)
        self._script_thread.start()

        self._start_dispatcher()


    def _render(self):
        """Renders the current light values without starting any threads."""
        current_lights = deepcopy(self.script.lights)

        for overlay in self.overlays:
            current_lights = overlay.apply(current_lights)

        return current_lights

    def stop(self):
        """Gracefully halts dispatcher, and kills the script."""
        if self._stop_dispatcher:
            self._stop_dispatcher()

        if self._script_thread and self._script_thread.is_alive():
            _force_kill_thread(self._script_thread)
        print("Scene stopped.")

class AudioScene(Scene):
    def __init__(self, bg: SceneScript, overlays: list[Overlay | AudioOverlay], callback: Callable[[LightConfig], None], playfromfile : bool = False ):
        super().__init__(bg, overlays, callback)
        self.audio_data = np.zeros(1024)
        self.playfromfile = playfromfile

    def _start_dispatcher(self):
        def handle_audio_data(indata: np.ndarray, frames: int, time, status):
            if status and str(status) == "input overflow":
                print("Input overflow. Could be caused by low latency selected",
                        file=sys.stderr)
                    
            self.audio_data = indata[:, 0]
            lights = self._render(self.audio_data)

            self.callback(lights)

        if self.playfromfile:
            self._stop_dispatcher = audio.bind_file("song.mp3", handle_audio_data, True, True)
        else:
            self._stop_dispatcher = audio.bind(handle_audio_data)

    def _render(self, audio_data: np.ndarray):
        """Renders the current light values without starting any threads."""
        current_lights = deepcopy(self.script.lights)

        for overlay in self.overlays:
            if isinstance(overlay, AudioOverlay):
                current_lights = overlay.apply(current_lights, audio_data)
            else:
                current_lights = overlay.apply(current_lights)

        return current_lights
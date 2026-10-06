import ctypes
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy
from enum import Enum
from pathlib import Path

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
        ctypes.c_ulong(thread_id), ctypes.py_object(SystemExit)
    )

    if res == 0:
        print("Error: Invalid thread ID.")
    elif res > 1:
        # If it affected more than one thread (which shouldn't happen), revert it
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), None)
        print("Error: Failed to safely abort thread cleanly, reverted.")


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


class SceneType(Enum):
    POLL = "poll"
    MIC = "mic"
    PLAYBACK = "playback"


class SceneConfig:
    def __init__(
        self,
        type: SceneType,
        poll_interval: float = 0.025,
        audio_file: Path | None = Path("song.mp3"),
        output_enabled: bool = True,
    ):
        self.type = type
        if self.type == SceneType.POLL:
            self.poll_interval = poll_interval
        elif self.type == SceneType.PLAYBACK:
            self.audio_file = audio_file
            self.output_enabled = output_enabled

    @classmethod
    def poll(cls, poll_interval=0.025) -> "SceneConfig":
        return cls(SceneType.POLL, poll_interval=poll_interval)

    @classmethod
    def mic(cls) -> "SceneConfig":
        return cls(SceneType.MIC)

    @classmethod
    def playback(
        cls, audio_file: Path | None = Path("song.mp3"), output_enabled: bool = True
    ) -> "SceneConfig":
        return cls(
            SceneType.PLAYBACK, audio_file=audio_file, output_enabled=output_enabled
        )


class Overlay(ABC):
    """Abstract base class for an overlay modifying light values."""

    @abstractmethod
    def apply(self, context: FrameContext) -> FrameContext:
        pass


class Scene(ABC):
    """
    Abstract base class for a scene.
    To make a new scene, subclass this and implement the run() method.
    Construct the scene and call start() to start.
    """

    def __init__(self, config: SceneConfig, overlays: list[Overlay] | None = None):
        self.config = config

        self.context = None
        """
        Stores the last context with which the scene was rendered.
        Will be None untill first call.
        """

        self.overlays = overlays or []

        self.lights = LightConfig()
        """
        The LightConfig object storing the config used by the run function.
        """

    @abstractmethod
    def run(self):
        """
        Runs when the scene is active.
        """

    def _start_poll_dispatcher(self, callback: Callable[[LightConfig], None]):
        dp_stop_event = threading.Event()

        def dispatcher_loop():
            interval = self.config.poll_interval
            next_frame = time.monotonic()

            while not dp_stop_event.is_set():
                current_lights = self._render(FrameContext())

                callback(current_lights)

                next_frame += interval
                delay = next_frame - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                else:
                    next_frame = time.monotonic()  # System lag recovery

        _dispatcher_thread = threading.Thread(target=dispatcher_loop, daemon=True)
        _dispatcher_thread.start()

        return dp_stop_event.set

    def _start_audio_dispatcher(self, callback: Callable[[LightConfig], None]):
        def handle_audio_data(indata: np.ndarray, frames: int, time, status):
            if status and str(status) == "input overflow":
                print(
                    "Input overflow. Could be caused by low latency selected",
                    file=sys.stderr,
                )

            context = FrameContext()
            context.audio_data = indata[:, 0]
            lights = self._render(context)

            callback(lights)

        if self.config.type == SceneType.PLAYBACK:
            return audio.bind_file(
                self.config.audio_file,
                handle_audio_data,
                True,
                self.config.output_enabled,
            )
        else:
            return audio.bind(handle_audio_data)

    def start_dispatcher(self, callback: Callable[[LightConfig], None]):
        if self.config.type == SceneType.POLL:
            return self._start_poll_dispatcher(callback)
        elif self.config.type in [SceneType.MIC, SceneType.PLAYBACK]:
            self._start_audio_dispatcher(callback)

    def _render(self, context: FrameContext) -> LightConfig:
        """Renders the current light values without starting any threads."""
        context.lights = self.lights
        self.context = context

        current_context = deepcopy(context)
        for overlay in self.overlays:
            current_context = overlay.apply(current_context)

        return current_context.lights

    def start(self):
        """Starts the user's run function on another thread."""

        def run_user_script():
            try:
                self.run()
                while True:
                    time.sleep(1)
            except SystemExit:
                # print("Background scene was forcibly terminated.")
                pass
            finally:
                self.stop()

        self._script_thread = threading.Thread(target=run_user_script, daemon=True)
        self._script_thread.start()

    def stop(self):
        """Kills the script."""

        if self._script_thread and self._script_thread.is_alive():
            _force_kill_thread(self._script_thread)
        print("Scene stopped.")

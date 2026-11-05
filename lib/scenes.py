import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from lib import audio
from lib.arion_lights import LightConfig
from lib.frame_context import FrameContext


class SceneType(Enum):
    POLL = "poll"
    MIC = "mic"
    PLAYBACK = "playback"


class SceneConfig:
    def __init__(
        self,
        type: SceneType,
        poll_interval: float = 0.025,
        audio_file: Path | None = None,
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
    def playback(cls, audio_file: Path, output_enabled: bool = True) -> "SceneConfig":
        return cls(
            SceneType.PLAYBACK, audio_file=audio_file, output_enabled=output_enabled
        )


class Layer(ABC):
    """Layer which makes up a scene. Is called every frame and modifies the light config. Can be disabled to skip processing."""

    def __init__(self, disabled: bool = False):
        super().__init__()
        self.disabled = disabled

    @abstractmethod
    def apply(self, context: FrameContext) -> FrameContext:
        pass


class Scene:
    """
    A Scene consiist of a set of layers and a configuration. It can be run in different modes, such as polling or audio playback.
    The scene can be started and will call the provided callback with the current light configuration at each frame.
    """

    def __init__(
        self,
        config: SceneConfig,
        background: LightConfig | None = None,
        layers: list[Layer] | None = None,
    ):
        self.config = config
        """Just if external scripts wanna know how its going. Shouldn't be used internally."""
        self.background = background or LightConfig()
        self.layers = layers or []
        self.start_time = None

    def _start_poll_dispatcher(self, callback: Callable[[LightConfig], None]):
        dp_stop_event = threading.Event()

        def dispatcher_loop():
            interval = self.config.poll_interval
            next_frame = time.monotonic()

            while not dp_stop_event.is_set():
                lights = self._render(FrameContext())

                callback(lights)

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
        def render(context: FrameContext):
            lights = self._render(context)

            callback(lights)

        if self.config.type == SceneType.PLAYBACK:
            return audio.bind_file(
                self.config.audio_file,
                render,
                self.config.output_enabled,
            )
        else:
            return audio.bind(render)

    def start_dispatcher(self, callback: Callable[[LightConfig], None]):
        """Starts the scene and begins dispatching light configurations to the provided callback."""
        self.start_time = time.monotonic()
        if self.config.type == SceneType.POLL:
            return self._start_poll_dispatcher(callback)
        elif self.config.type in [SceneType.MIC, SceneType.PLAYBACK]:
            self._start_audio_dispatcher(callback)

    def pre_render(self, context: FrameContext) -> FrameContext:
        """Function to be called before rendering the scene. Can be overridden to modify: the context, the layers, or the background. Returns the context to be used for rendering."""
        return context

    def _render(self, context: FrameContext) -> LightConfig:
        """Renders the current light values without starting any threads."""
        self.context = self.pre_render(context)

        t = time.monotonic() - self.start_time if self.start_time is not None else None
        aud = context.audio_data.copy() if context.audio_data is not None else None
        current_context = FrameContext(
            lights=self.background.copy(),
            time=t,
            audio_data=aud,
            playback_timestamp=context.timestamp,
            sampling_rate=context.sampling_rate,
        )
        for overlay in self.layers:
            if not overlay.disabled:
                current_context = overlay.apply(current_context)

        return current_context.lights

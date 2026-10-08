import sys
import time
from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd
import soundfile as sf

from lib.frame_context import FrameContext

_current_stream = None
blocksize = 1024


def select_device(
    device_name: str = "Razer Seiren Mini", auto: bool = False, print_info: bool = True
) -> int:
    """Selects an input device, falling back to defaults or auto-selection."""
    global sampling_rate

    try:
        inputdev = sd.query_devices(device_name)  # default device takes priority
    except ValueError:
        if auto:
            inputdev = sd.query_devices(sd.default.device[0])
            print(f"Auto selected - {inputdev['name']}")
        else:
            print(sd.query_devices())
            inp = input("Select a device: ")
            try:
                inputdev = sd.query_devices(inp)
            except ValueError:
                inputdev = sd.query_devices(int(inp))

    inputdevind = inputdev["index"]
    sampling_rate = inputdev["default_samplerate"]
    channels = inputdev["max_input_channels"]

    if print_info:
        print("Input device:")
        print(f"  Name       {inputdev['name']}")
        print(f"  LowLatency {inputdev['default_low_input_latency'] * 1000} ms")
        print(f"  HighLatency {inputdev['default_high_input_latency'] * 1000} ms")
        print(f"  SampleRate {sampling_rate}")
        print(f"  UpdateRate {sampling_rate / blocksize} hz")
        print(f"  Channels   {channels}")
        if "hw" not in inputdev["name"]:
            print('WARNING could not find "hw" in device name')
            print("This could be a sign of a virtual device")
            print("This may introduce a lot of lag")

    if channels == 0:
        raise ValueError("Max possible channel count 0 :(")

    return inputdevind

def bind(
    callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None],
    device: int | None = None,
) -> tuple[Callable[[], None], Callable[[], None]]:
    """Binds a callback to a new live audio input stream.

    Raises RuntimeError if a stream is already active.
    Returns a stop function to halt and clean up the stream.
    """
    global _current_stream

    if _current_stream is not None and _current_stream.active:
        raise RuntimeError(
            "Cannot bind a new stream: the previous audio stream is still running."
        )

    if device is None:
        device = select_device(auto=True)

    def stream_callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)

        context = FrameContext()
        context.audio_data = indata[:, 0]
        context.sampling_rate = sampling_rate

        callback(context)

    _current_stream = sd.InputStream(
        device=device,
        blocksize=blocksize,
        channels=1,
        samplerate=sampling_rate,
        latency=None,
        callback=stream_callback,
    )
    _current_stream.start()
    print("Audio input stream started.")

    def stop_stream():
        global _current_stream
        if _current_stream is not None:
            _current_stream.stop()
            _current_stream.close()
            _current_stream = None
            print("Audio stream stopped.")

    return _current_stream.start, stop_stream


fileblockdelay: int = -3
"""
+ means playback delayed
- means lights delayed
"""
_delay_buffer = None
_buffer_pos = None
timestamp = None


def bind_file(
    filepath: str,
    callback: Callable[[FrameContext], None],
    loop: bool = False,
    speaker_output: bool = True,
) -> tuple[Callable[[], None], Callable[[], None]]:
    """Plays an audio file, optionally streams data to speakers, and calls
    the provided callback with frame context.

    Raises RuntimeError if a stream is already active.
    Returns a stop function to halt and clean up playback.
    """
    global timestamp, _delay_buffer, _buffer_pos

    # Open the audio file
    file = sf.SoundFile(filepath)
    sampling_rate = file.samplerate
    channels = file.channels
    timestamp = 0
    _delay_buffer = np.zeros((abs(int(fileblockdelay)), blocksize, channels))
    _buffer_pos = 0

    print(f"Opening audio file: {filepath} ({sampling_rate} Hz, {channels} channels)")

    def file_callback(outdata, frames, _, status):
        global timestamp, _delay_buffer, _buffer_pos

        start = time.monotonic()
        if status:
            print(status, file=sys.stderr)

        data = file.read(frames, dtype="float32", always_2d=True)

        # Handle file exhaustion and looping
        if len(data) < frames:
            if loop:
                file.seek(0)
                remaining = frames - len(data)
                data_extra = file.read(remaining, dtype="float32", always_2d=True)
                data = np.concatenate((data, data_extra), axis=0)
            else:
                # Pad the remainder with zeros
                data = np.pad(data, ((0, frames - len(data)), (0, 0)))

        if fileblockdelay:
            if abs(int(fileblockdelay)) != np.size(_delay_buffer, 0):
                _delay_buffer = np.resize(
                    _delay_buffer, (abs(int(fileblockdelay)), blocksize, channels)
                )

            _buffer_pos = _buffer_pos % abs(int(fileblockdelay))
            buffered = _delay_buffer[_buffer_pos].copy()
            _delay_buffer[_buffer_pos] = data
            _buffer_pos += 1

        # Stream to speakers if enabled, otherwise mute output buffer
        if speaker_output:
            if fileblockdelay > 0:
                outdata[:] = buffered
            else:
                outdata[:] = data
        else:
            outdata.fill(0)

        context = FrameContext()
        if fileblockdelay < 0:
            context.audio_data = buffered[:, 0]
        else:
            context.audio_data = data[:, 0]

        context.timestamp = timestamp
        context.sampling_rate = sampling_rate

        timestamp += len(data) / sampling_rate

        # Trigger the user callback with the context
        callback(context)

        # processing_time should not exceed 25% of the available time
        processing_time = time.monotonic() - start
        available = blocksize / sampling_rate
        if processing_time > 0.5 * available:
            print("Processing time too slow!")
            print(f"{processing_time * 1000}ms used")
            print(f"{available * 1000}ms available")

    stream = sd.OutputStream(
        samplerate=sampling_rate,
        blocksize=blocksize,
        channels=channels,
        callback=file_callback,
    )
    stream.start()
    print("Audio file playback stream started.")

    def stop_stream():
        file.close()
        if stream is not None:
            stream.stop()
            stream.close()
            print("Audio file stream stopped.")

    return stop_stream

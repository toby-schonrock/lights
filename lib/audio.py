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
) -> Callable[[], None]:
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


playback_frame_delay: int = -8 # can be negative

def bind_file(
    filepath: str,
    callback: Callable[[FrameContext], None],
    speaker_output: bool = True,
) -> Callable[[], None]:
    """Plays an audio file, optionally streams data to speakers, and calls
    the provided callback with frame context.

    Raises RuntimeError if a stream is already active.
    Returns a stop function to halt and clean up playback.
    """
    # Read entire audio file
    data, sampling_rate = sf.read(filepath, always_2d=True)
    data = np.pad(data, ((0, blocksize - (len(data) % blocksize)), (0,0)))
    assert len(data) % blocksize == 0
    channels = data.shape[1]
    frame_idx = 0
    empty_frame = np.zeros((blocksize, channels))

    print(f"Read audio file: {filepath} ({sampling_rate} Hz, {channels} channels)")

    def read_block(start_idx):
        """Always call this with a multiple of block size"""
        end = start_idx + blocksize
        if start_idx < 0 or end > len(data):
            return empty_frame
        return data[start_idx:end]

    def file_callback(outdata, frames, _, status):
        nonlocal frame_idx
        start = time.monotonic()
        if status:
            print(status, file=sys.stderr)

        # Stream to speakers if enabled, otherwise mute output buffer
        if speaker_output:
            outdata[:] = read_block(frame_idx - int(playback_frame_delay) * blocksize)
        else:
            outdata.fill(0)

        context = FrameContext()

        context.audio_data = read_block(frame_idx)[:, 0].copy()
        context.timestamp = frame_idx / sampling_rate
        context.sampling_rate = sampling_rate

        frame_idx = (frame_idx + blocksize) % len(data)

        # Trigger the user callback with the context
        callback(context)

        # processing_time should not exceed 25% of the available time
        processing_time = time.monotonic() - start
        available = blocksize / sampling_rate
        if processing_time > 0.5 * available:
            print("Processing time too slow!")
            print(f"{processing_time * 1000}ms used")
            print(f"{available * 1000}ms available")

    # try catch wrapper for comfort maybe remove later
    def safe_file_callback(outdata, frames, _, status):
        try:
            file_callback(outdata, frames, _, status)
        except:
            print("Runtime error in audio callback")
            raise

    stream = sd.OutputStream(
        samplerate=sampling_rate,
        blocksize=blocksize,
        channels=channels,
        callback=safe_file_callback,
    )
    stream.start()
    print("Audio file playback stream started.")

    def stop_stream():
        if stream is not None:
            stream.stop()
            stream.close()
            print("Audio file stream stopped.")

    return stop_stream

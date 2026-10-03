from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd
import soundfile as sf

_current_stream = None
inputdevind = None
blocksize = 1024
samplingrate = None

def select_device(auto: bool = False, print_info: bool = True, device_name: str = "Razer Seiren Mini"):
    """Selects an input device, falling back to defaults or auto-selection."""
    global inputdevind, samplingrate

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

    inputdevind = inputdev['index']
    samplingrate = inputdev['default_samplerate']
    channels = inputdev['max_input_channels']

    if print_info:
        print("Input device:")
        print(f"  Name       {inputdev['name']}")
        print(f"  LowLatency {inputdev['default_low_input_latency'] * 1000} ms")
        print(f"  HighLatency {inputdev['default_high_input_latency'] * 1000} ms")
        print(f"  SampleRate {samplingrate}")
        print(f"  UpdateRate {samplingrate / blocksize} hz")
        print(f"  Channels   {channels}")
        if "hw" not in inputdev['name']:
            print('WARNING could not find "hw" in device name')
            print('This could be a sign of a virtual device')
            print('This may introduce a lot of lag')

    if channels == 0:
        raise ValueError("Max possible channel count 0 :(")

def bind(callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None]) -> Callable[[], None]:
    """Binds a callback to a new live audio input stream.
    
    Raises RuntimeError if a stream is already active.
    Returns a stop function to halt and clean up the stream.
    """
    global _current_stream

    if _current_stream is not None and _current_stream.active:
        raise RuntimeError("Cannot bind a new stream: the previous audio stream is still running.")

    if inputdevind is None:
        select_device(auto=True)

    _current_stream = sd.InputStream(
        device=inputdevind,
        blocksize=blocksize,
        channels=1,
        samplerate=samplingrate,
        latency=None,
        callback=callback
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

    return stop_stream

def bind_file(
    filepath: str, 
    callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None], 
    loop: bool = False, 
    speaker_output: bool = True
) -> Callable[[], None]:
    """Plays an audio file, optionally streams data to speakers, and calls 
    the provided callback with the audio chunks.
    
    Raises RuntimeError if a stream is already active.
    Returns a stop function to halt and clean up playback.
    """
    global _current_stream

    if _current_stream is not None and _current_stream.active:
        raise RuntimeError("Cannot bind a new stream: the previous audio stream is still running.")

    # Open the audio file
    f = sf.SoundFile(filepath)
    file_sr = f.samplerate
    channels = f.channels

    print(f"Opening audio file: {filepath} ({file_sr} Hz, {channels} channels)")

    def file_callback(outdata, frames, time_info, status):
        if status:
            print(status)
        
        data = f.read(frames, dtype='float32', always_2d=True)
        
        # Handle file exhaustion and looping
        if len(data) < frames:
            if loop:
                f.seek(0)
                remaining = frames - len(data)
                data_extra = f.read(remaining, dtype='float32', always_2d=True)
                data = np.concatenate((data, data_extra), axis=0)
            else:
                # Pad the remainder with zeros
                data = np.pad(data, ((0, frames - len(data)), (0, 0)))

        # Stream to speakers if enabled, otherwise mute output buffer
        if speaker_output:
            outdata[:] = data
        else:
            outdata.fill(0)

        # Trigger the user callback with the audio chunk
        callback(data, frames, time_info, status)

    _current_stream = sd.OutputStream(
        samplerate=file_sr,
        blocksize=blocksize,
        channels=channels,
        callback=file_callback
    )
    _current_stream.start()
    print("Audio file playback stream started.")

    def stop_stream():
        global _current_stream
        f.close()
        if _current_stream is not None:
            _current_stream.stop()
            _current_stream.close()
            _current_stream = None
            print("Audio file stream stopped.")

    return stop_stream
from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd

_current_stream = None
inputdevind = None
blocksize = 1024
samplingrate = None

def select_device(auto = False, print_info = True):
    global inputdevind, samplingrate

    try:
        inputdev = sd.query_devices("Razer Seiren Mini")  # default device always takes priority
    except ValueError:
        if auto:
            inputdev = sd.query_devices(sd.default.device)
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
        print(f"  HigLatency {inputdev['default_high_input_latency'] * 1000} ms")
        print(f"  SampleRate {samplingrate}")
        print(f"  UpdateRate {samplingrate / blocksize} hz")
        print(f"  Channels   {channels}")
        if ("hw" not in inputdev['name']):
            print('WARNING could not find "hw" in device name')
            print('This could be a sign of a virtual device')
            print('This may introduce a lot of lag')

    if channels == 0:
        raise ValueError("Max possible channel count 0 :(")

def bind(callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None]) -> Callable[[], None]:
    """Binds a callback to a new audio input stream.
    Callback signature: indata: numpy.ndarray, frames: int,
    time: CData, status: CallbackFlags

    Raises RuntimeError if a stream is already active.
    Returns a stop function to halt and clean up the stream.
    """
    global _current_stream, inputdevind, samplingrate

    if _current_stream is not None and _current_stream.active:
        raise RuntimeError("Cannot bind a new stream: the previous audio stream is still running.")

    if inputdevind is None:
        raise RuntimeError("Cannot bind a new stream: no device selected. Call audio.select_device()")

    _current_stream = sd.InputStream(
        device=inputdevind,
        blocksize=blocksize,
        channels=1,
        latency=None, # for some reason better than 'low'
        callback=callback,
        samplerate=samplingrate
    )
    _current_stream.start()
    print("Audio stream started.")

    def stop_stream():
        global _current_stream
        if _current_stream is not None:
            _current_stream.stop()
            _current_stream.close()
            _current_stream = None
            print("Audio stream stopped.")


    return stop_stream
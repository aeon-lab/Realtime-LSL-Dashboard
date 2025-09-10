"""
Dummy LSL Signal Stream
----------------------
This script generates a variety of synthetic signals and streams them over
Lab Streaming Layer (LSL). It can be used for testing real-time visualization
dashboards, signal processing pipelines, or machine learning experiments.

Features:
- 10 signal types: sine, cosine, square, sawtooth, triangle, step, random noise,
  exponential decay, pulse train, and chirp.
- Configurable sampling rate and channel labels.
- Sends data over LSL using a named stream ("Dummy Stream").

Dependencies:
    pip install numpy pylsl
"""

import numpy as np
import time
from pylsl import StreamInfo, StreamOutlet

# -----------------------------------------------------------------------------
# SIGNAL DEFINITIONS
# -----------------------------------------------------------------------------
# Each function defines a synthetic signal. Time 't' is the input (in seconds).

def sine_wave(t, freq=10, amp=1.0):
    """Sine wave with frequency `freq` Hz and amplitude `amp`."""
    return amp * np.sin(2 * np.pi * freq * t)

def cosine_wave(t, freq=10, amp=1.0):
    """Cosine wave with frequency `freq` Hz and amplitude `amp`."""
    return amp * np.cos(2 * np.pi * freq * t)

def square_wave(t, freq=1, amp=1.0):
    """Square wave toggling between +amp and -amp at frequency `freq` Hz."""
    return amp * np.sign(np.sin(2 * np.pi * freq * t))

def sawtooth_wave(t, freq=1, amp=1.0):
    """Sawtooth wave linearly rising and dropping every period."""
    return amp * (2 * (t * freq % 1) - 1)

def triangle_wave(t, freq=1, amp=1.0):
    """Triangle wave oscillating between -amp and +amp."""
    return amp * (2 * np.abs(2 * (t * freq % 1) - 1) - 1)

def step_signal(t, amp=1.0):
    """Step signal alternating between `amp` and 0 every 1 second."""
    return amp if t % 2 < 1 else 0

def random_noise(t, amp=1.0):
    """Random Gaussian noise with standard deviation `amp`."""
    return amp * np.random.randn()

def exponential_decay(t, amp=1.0, decay=0.1):
    """Exponential decay signal with decay rate `decay`."""
    return amp * np.exp(-decay * t)

def pulse_train(t, freq=10, amp=1.0):
    """Pulse train: alternating between `amp` and 0 at `freq` Hz."""
    return amp if int(t * freq) % 2 == 0 else 0

def chirp_signal(t, f0=1, f1=20, T=10, amp=1.0):
    """
    Linear chirp signal increasing frequency from f0 to f1 over duration T.
    This example uses t**5 for a slow sweep (nonlinear chirp).
    """
    k = (f1 - f0) / T
    return amp * np.sin(2 * np.pi * (f0 * t + 0.5 * k * t**5))


# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
sampling_rate = 100  # Hz, number of samples per second

# Channel names corresponding to each signal generator
channel_labels = [
    "SineWave", "CosineWave", "SquareWave", "SawtoothWave", "TriangleWave",
    "StepSignal", "RandomNoise", "ExponentialDecay", "PulseTrain", "ChirpSignal"
]

# List of signal generator functions in same order as labels
signal_generators = [
    sine_wave, cosine_wave, square_wave, sawtooth_wave, triangle_wave,
    step_signal, random_noise, exponential_decay, pulse_train, chirp_signal
]

channel_count = len(signal_generators)


# -----------------------------------------------------------------------------
# CREATE LSL STREAM
# -----------------------------------------------------------------------------
# StreamInfo defines metadata for the LSL outlet
info = StreamInfo(
    name="Dummy Stream",       # Stream name visible to clients
    type="EEG",                # Type of data
    channel_count=channel_count,
    nominal_srate=sampling_rate,
    channel_format='float32',
    source_id="dummy_stream_001"
)

# Add channel labels as metadata
channels = info.desc().append_child("channels")
for label in channel_labels:
    ch = channels.append_child("channel")
    ch.append_child_value("label", label)

# Create LSL outlet to send data
outlet = StreamOutlet(info)
print(f"Started LSL stream 'Dummy Stream' with {channel_count} channels at {sampling_rate} Hz.")


# -----------------------------------------------------------------------------
# STREAMING LOOP
# -----------------------------------------------------------------------------
t0 = time.time()  # reference start time
try:
    while True:
        t = time.time() - t0          # elapsed time in seconds
        sample = [gen(t) for gen in signal_generators]  # generate sample for all channels
        outlet.push_sample(sample)    # push sample to LSL
        time.sleep(1.0 / sampling_rate)  # maintain target sampling rate

except KeyboardInterrupt:
    # Stop gracefully on Ctrl+C
    print("Stream stopped.")

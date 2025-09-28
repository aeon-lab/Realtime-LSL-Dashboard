"""
Mouse Input LSL Stream (Single Stream)
----------------------
This script captures mouse movement, click, and scroll data and streams it over
Lab Streaming Layer (LSL) in a single stream.

Features:
- Single stream containing: X, Y coordinates, button states, and scroll values
- Configurable sampling rate
- Real-time mouse event capture

Dependencies:
    pip install numpy pylsl pynput
"""

import numpy as np
import time
from pylsl import StreamInfo, StreamOutlet
from pynput import mouse
from collections import deque
import threading

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
sampling_rate = 100  # Hz, number of samples per second

# Mouse data storage with thread-safe deque
mouse_data = {
    'position': deque(maxlen=10),  # Store recent positions (x, y)
    'buttons': deque(maxlen=10),   # Store recent button states (left, middle, right)
    'scroll': deque(maxlen=10)     # Store scroll events (x, y)
}

# Initialize with default values
mouse_data['position'].append((0, 0))
mouse_data['buttons'].append((0, 0, 0))
mouse_data['scroll'].append((0, 0))

# -----------------------------------------------------------------------------
# MOUSE EVENT HANDLERS
# -----------------------------------------------------------------------------
def on_move(x, y):
    """Callback for mouse movement events."""
    mouse_data['position'].append((x, y))

def on_click(x, y, button, pressed):
    """Callback for mouse click events."""
    # Convert button state to numeric values
    left = 1 if (button == mouse.Button.left and pressed) else 0
    middle = 1 if (button == mouse.Button.middle and pressed) else 0
    right = 1 if (button == mouse.Button.right and pressed) else 0

    mouse_data['buttons'].append((left, middle, right))

def on_scroll(x, y, dx, dy):
    """Callback for mouse scroll events."""
    mouse_data['scroll'].append((dx, dy))

# -----------------------------------------------------------------------------
# CREATE SINGLE LSL STREAM
# -----------------------------------------------------------------------------
# Single stream containing all mouse data (7 channels total)
stream_info = StreamInfo(
    name="MouseData",
    type="Mouse",
    channel_count=7,  # X, Y, Left, Middle, Right, ScrollX, ScrollY
    nominal_srate=sampling_rate,
    channel_format='float32',
    source_id="mouse_data_001"
)

# Add channel labels and metadata
channels = stream_info.desc().append_child("channels")

# Position channels
channels.append_child("channel").append_child_value("label", "MouseX")
channels.append_child("channel").append_child_value("label", "MouseY")

# Button channels
channels.append_child("channel").append_child_value("label", "LeftButton")
channels.append_child("channel").append_child_value("label", "MiddleButton")
channels.append_child("channel").append_child_value("label", "RightButton")

# Scroll channels
channels.append_child("channel").append_child_value("label", "ScrollX")
channels.append_child("channel").append_child_value("label", "ScrollY")

# Add stream metadata
stream_info.desc().append_child_value("description", "Combined mouse data stream")
stream_info.desc().append_child_value("manufacturer", "MouseLSL")
stream_info.desc().append_child_value("units", "pixels for position, binary for buttons, delta for scroll")

# Create LSL outlet
outlet = StreamOutlet(stream_info)

print(f"Started LSL stream 'MouseData' with 7 channels at {sampling_rate} Hz.")
print("Channels: MouseX, MouseY, LeftButton, MiddleButton, RightButton, ScrollX, ScrollY")

# -----------------------------------------------------------------------------
# MOUSE LISTENER THREAD
# -----------------------------------------------------------------------------
def start_mouse_listener():
    """Start the mouse listener in a separate thread."""
    listener = mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll
    )
    listener.start()
    return listener

# -----------------------------------------------------------------------------
# STREAMING LOOP
# -----------------------------------------------------------------------------
def main():
    # Start mouse listener
    mouse_listener = start_mouse_listener()
    print("Mouse listener started. Move your mouse or click to generate data.")
    print("Press Ctrl+C to stop streaming.")

    try:
        while True:
            # Get the most recent mouse data
            current_pos = mouse_data['position'][-1] if mouse_data['position'] else (0, 0)
            current_buttons = mouse_data['buttons'][-1] if mouse_data['buttons'] else (0, 0, 0)
            current_scroll = mouse_data['scroll'][-1] if mouse_data['scroll'] else (0, 0)

            # Combine all data into a single sample (7 channels)
            sample = [
                float(current_pos[0]),      # MouseX
                float(current_pos[1]),      # MouseY
                float(current_buttons[0]),  # LeftButton
                float(current_buttons[1]),  # MiddleButton
                float(current_buttons[2]),  # RightButton
                float(current_scroll[0]),   # ScrollX
                float(current_scroll[1])    # ScrollY
            ]

            # Push the combined sample to LSL
            outlet.push_sample(sample)

            # Clear scroll data after sending (scroll events are momentary)
            if len(mouse_data['scroll']) > 1:
                mouse_data['scroll'].clear()
                mouse_data['scroll'].append((0, 0))  # Reset to zero

            time.sleep(1.0 / sampling_rate)

    except KeyboardInterrupt:
        # Stop gracefully on Ctrl+C
        print("\nStopping streams...")
        mouse_listener.stop()
        print("Streams stopped.")

if __name__ == "__main__":
    main()
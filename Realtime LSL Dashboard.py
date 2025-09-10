"""
Realtime LSL Dashboard
--------------
A Python-based realtime GUI dashboard to visualize Lab Streaming Layer (LSL) signals using Tkinter + Matplotlib.

Features:
- Automatic LSL stream discovery (periodically refreshed).
- Dropdown to select active stream for visualization.
- Real-time scrolling plots for multi-channel signals.
- Auto-pause when no data is received (freeze feature).
- Start/Pause controls for visualization.
- Logos/branding footer (Auburn University + ÆON Lab). Feel free to add yours if needed with proper citations.

Dependencies:
    pip install pylsl matplotlib numpy
"""

import sys
import os
import math
import time
import threading
from collections import deque

import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for Tkinter integration
import matplotlib.pyplot as plt

from pylsl import StreamInlet, resolve_streams
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# -----------------------------------------------------------------------------
# CONFIGURATION PARAMETERS
# -----------------------------------------------------------------------------
plot_duration = 10           # seconds of data shown in plots
update_interval = 0.05       # plot update interval (in seconds)
sampling_rate_guess = 100    # fallback if stream does not provide sampling rate
max_no_data_count = 5        # freeze after these many consecutive no-data events

# -----------------------------------------------------------------------------
# GLOBAL VARIABLES
# -----------------------------------------------------------------------------
stream_info = []             # list of discovered LSL stream info dictionaries
stream_names = []            # list of discovered stream names
buffers = None               # holds time and channel data buffers
lines = []                   # matplotlib line objects for plotting
lines_axes = []              # corresponding axes for each channel
buf_len = 0                  # buffer length (samples)
fig = None                   # matplotlib figure
axes = None                  # figure axes
canvas = None                # tkinter canvas for embedding matplotlib
selected_stream_var = None   # tkinter StringVar for dropdown menu
start_time = time.time()

visualization_running = True
no_data_counter = 0
frozen_due_to_no_data = False


# -----------------------------------------------------------------------------
# STREAM BUFFER AND PLOT SETUP
# -----------------------------------------------------------------------------
def setup_stream_buffers_and_plots(stream_idx):
    """
    Initialize data buffers and subplots for the selected stream.
    Called whenever a stream is selected from the dropdown.
    """
    global buffers, lines, lines_axes, buf_len, fig, axes, canvas

    if not stream_info:
        # No streams found → clear canvas
        fig.clf()
        canvas.draw()
        canvas.get_tk_widget().update()
        return

    # Remove old canvas widget before recreating it
    canvas.get_tk_widget().pack_forget()
    canvas.get_tk_widget().destroy()

    # Extract stream metadata
    stream = stream_info[stream_idx]
    ch_count = stream['ch_count']
    srate = stream['srate']
    buf_len = int(plot_duration * srate)

    # Create subplot grid layout (5 columns)
    cols = 5
    rows = math.ceil(ch_count / cols)
    fig = plt.figure(figsize=(10, 3 * rows))
    axes = fig.subplots(rows, cols, squeeze=False)

    # Recreate canvas with new figure
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill='both', expand=True)

    # Initialize buffers
    time_buffer = deque(maxlen=buf_len)
    channel_buffers = [deque(maxlen=buf_len) for _ in range(ch_count)]

    lines.clear()
    lines_axes.clear()

    # Create plots for each channel
    for ch in range(ch_count):
        row = ch // cols
        col = ch % cols
        ax = axes[row][col]
        ax.set_xlim(0, plot_duration)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel(stream['ch_labels'][ch])
        line, = ax.plot([], [])
        lines.append(line)
        lines_axes.append(ax)

    # Remove unused axes in last row
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if idx >= ch_count:
                fig.delaxes(axes[r][c])

    # Title for the figure
    fig.suptitle(stream['name'], fontsize=14, fontweight='bold')
    buffers = (time_buffer, channel_buffers)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    canvas.draw()
    canvas.get_tk_widget().update()


# -----------------------------------------------------------------------------
# STREAM SELECTION HANDLER
# -----------------------------------------------------------------------------
def on_stream_select():
    """Callback when a new stream is selected from the dropdown."""
    if not stream_info:
        return
    stream_name = selected_stream_var.get()
    if stream_name in stream_names:
        idx = stream_names.index(stream_name)
        setup_stream_buffers_and_plots(idx)
        start_visualization()  # auto start visualization after selection


# -----------------------------------------------------------------------------
# LIVE PLOT UPDATER
# -----------------------------------------------------------------------------
def update_plot():
    """
    Periodic function (via root.after) that:
    - Pulls data from selected stream
    - Updates buffers
    - Redraws plots
    """
    global no_data_counter, frozen_due_to_no_data

    if not plt.fignum_exists(fig.number):
        root.quit()
        return

    if not stream_info:
        root.after(int(update_interval * 1000), update_plot)
        return

    stream_name = selected_stream_var.get()
    if stream_name not in stream_names:
        root.after(int(update_interval * 1000), update_plot)
        return

    if not visualization_running:
        root.after(int(update_interval * 1000), update_plot)
        return

    idx = stream_names.index(stream_name)
    inlet = stream_info[idx]['inlet']
    time_buffer, channel_buffers = buffers

    # Try pulling sample from LSL inlet
    try:
        sample, timestamp = inlet.pull_sample(timeout=0.1)
    except Exception as e:
        print(f"Error pulling sample: {e}")
        sample = None

    if sample:
        # Reset freeze counters
        no_data_counter = 0
        frozen_due_to_no_data = False
        now = time.time() - start_time
        time_buffer.append(now)
        for ch, val in enumerate(sample):
            channel_buffers[ch].append(val)
    else:
        # No data received
        no_data_counter += 1
        if no_data_counter > max_no_data_count:
            if not frozen_due_to_no_data:
                print("No data received for a while; freezing visualization.")
                frozen_due_to_no_data = True
            root.after(int(update_interval * 1000), update_plot)
            return

    # Update plots if buffer has data
    if len(time_buffer) > 0:
        now = time_buffer[-1]
        x_start = max(0, now - plot_duration)
        for ch in range(len(channel_buffers)):
            xdata = list(time_buffer)
            ydata = list(channel_buffers[ch])
            lines[ch].set_data(xdata, ydata)
            ax = lines_axes[ch]
            ax.relim()
            ax.autoscale_view()
            ax.set_xlim(x_start, now)

    canvas.draw()
    root.after(int(update_interval * 1000), update_plot)


# -----------------------------------------------------------------------------
# START/STOP VISUALIZATION
# -----------------------------------------------------------------------------
def start_visualization():
    """Enable live updates."""
    global visualization_running, no_data_counter, frozen_due_to_no_data
    if not visualization_running:
        print("Starting visualization...")
    visualization_running = True
    no_data_counter = 0
    frozen_due_to_no_data = False

def stop_visualization():
    """Pause live updates."""
    global visualization_running
    if visualization_running:
        print("Pausing visualization...")
    visualization_running = False


# -----------------------------------------------------------------------------
# BACKGROUND STREAM DISCOVERY
# -----------------------------------------------------------------------------
def discover_streams_background():
    """Discover LSL streams in a background thread (non-blocking)."""
    def worker():
        global stream_info, stream_names

        print("Background: Looking for LSL streams (timeout = 2s)...")
        try:
            streams = resolve_streams(wait_time=2.0)
        except Exception as e:
            print("Error resolving streams:", e)
            streams = []

        new_stream_info = []
        new_stream_names = []

        # Extract metadata for each stream
        for stream in streams:
            inlet = StreamInlet(stream)
            info = inlet.info()
            name = info.name()
            channel_count = info.channel_count()
            srate = int(info.nominal_srate() or sampling_rate_guess)

            # Try to fetch channel labels
            ch_labels = []
            try:
                channels_elem = info.desc().child("channels")
                ch_elem = channels_elem.child("channel")
                while ch_elem and not ch_elem.empty():
                    label = ch_elem.child_value("label")
                    if label:
                        ch_labels.append(label)
                    ch_elem = ch_elem.next_sibling()
            except Exception:
                pass

            if len(ch_labels) != channel_count:
                ch_labels = [f"Ch {i+1}" for i in range(channel_count)]

            new_stream_info.append({
                'name': name,
                'ch_labels': ch_labels,
                'ch_count': channel_count,
                'srate': srate,
                'inlet': inlet
            })
            new_stream_names.append(name)

        if not new_stream_info:
            new_stream_names.append("No Streams Found")

        # Update GUI in main thread
        def update_ui():
            selected_stream = selected_stream_var.get() if selected_stream_var else None
            if new_stream_names != stream_names or selected_stream not in new_stream_names:
                stream_info.clear()
                stream_info.extend(new_stream_info)
                stream_names.clear()
                stream_names.extend(new_stream_names)
                dropdown['values'] = stream_names

                if selected_stream in stream_names:
                    selected_stream_var.set(selected_stream)
                else:
                    selected_stream_var.set(stream_names[0])
                    if stream_info and visualization_running:
                        setup_stream_buffers_and_plots(0)
                    else:
                        fig.clf()
                        canvas.draw()
        root.after(0, update_ui)

    threading.Thread(target=worker, daemon=True).start()

def periodic_discover_streams():
    """Periodically rediscover streams every 5 seconds."""
    discover_streams_background()
    root.after(5000, periodic_discover_streams)


# -----------------------------------------------------------------------------
# GUI SETUP
# -----------------------------------------------------------------------------
root = tk.Tk()
root.title("ÆON LSL Viewer")
root.attributes('-fullscreen', False)

# Style tweaks
style = ttk.Style()
style.configure("TCombobox", font=("Arial", 16))
style.configure("TCombobox", padding=5)
root.option_add("*TCombobox*Listbox.Font", ("Aptos", 12))

# Top control panel
top_frame = tk.Frame(root)
top_frame.pack(fill='x', padx=10, pady=5)

selected_stream_var = tk.StringVar(value="No Streams Found")
dropdown = ttk.Combobox(top_frame, values=["No Streams Found"],
                        textvariable=selected_stream_var, state="readonly")
dropdown.pack(side='left', fill='x', expand=True, padx=(0, 5))
dropdown.bind("<<ComboboxSelected>>", lambda e: on_stream_select())

discover_btn = tk.Button(top_frame, text="Discover Streams", command=discover_streams_background)
discover_btn.pack(side='left', padx=(0, 5))

start_btn = tk.Button(top_frame, text="Start Visualization", command=start_visualization)
start_btn.pack(side='left', padx=(0, 5))

pause_btn = tk.Button(top_frame, text="Pause Visualization", command=stop_visualization)
pause_btn.pack(side='left')

# Default figure
fig, axes = plt.subplots(1, 1, figsize=(10, 4))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill='both', expand=True)

# Footer with logos
logo_frame = tk.Frame(root)
logo_frame.pack(side='bottom', fill='x', padx=10, pady=(0, 10))

try:
    auburn_logo = tk.PhotoImage(file="auburn_logo.png")
    auburn_label = tk.Label(logo_frame, image=auburn_logo)
except Exception:
    auburn_logo = None
    auburn_label = tk.Label(logo_frame, text="Auburn University", font=("Arial", 14, "bold"))
auburn_label.pack(side='left')

try:
    aeon_logo = tk.PhotoImage(file="aeon_logo.png")
    aeon_label = tk.Label(logo_frame, image=aeon_logo)
except Exception:
    aeon_logo = None
    aeon_label = tk.Label(logo_frame, text="ÆON Lab", font=("Arial", 14, "bold"))
aeon_label.pack(side='right')

# -----------------------------------------------------------------------------
# APP STARTUP
# -----------------------------------------------------------------------------
discover_streams_background()          # Initial discovery
root.after(5000, periodic_discover_streams)  # Background rediscovery
root.after(100, update_plot)           # Start live update loop
root.mainloop()

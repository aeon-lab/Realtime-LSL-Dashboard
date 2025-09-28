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
import matplotlib

matplotlib.use('TkAgg')  # Must be before importing pyplot

import numpy as np
import matplotlib.pyplot as plt
from pylsl import StreamInlet, resolve_streams
from collections import deque
import time
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
import threading

# --- Config ---
plot_duration = 10
update_interval = 0.05
sampling_rate_guess = 100
max_no_data_count = 5  # consecutive no-data samples before freezing visualization

# --- Global vars ---
stream_info = []
stream_names = []
buffers = None
lines = []
lines_axes = []
buf_len = 0
fig = None
axes = None
selected_stream_var = None
canvas = None
start_time = time.time()

visualization_running = True
no_data_counter = 0
frozen_due_to_no_data = False


def setup_stream_buffers_and_plots(stream_idx):
    global buffers, lines, lines_axes, buf_len, fig, axes, canvas

    if not stream_info:
        if fig:
            fig.clf()
            if canvas:
                canvas.draw()
        return

    # Clear old canvas properly
    if canvas:
        canvas.get_tk_widget().pack_forget()
        canvas.get_tk_widget().destroy()

    stream = stream_info[stream_idx]
    ch_count = stream['ch_count']
    srate = stream['srate']
    buf_len = int(plot_duration * srate)

    # Create new figure and layout
    cols = min(5, ch_count)  # Avoid too many columns for few channels
    rows = math.ceil(ch_count / cols)
    fig = plt.figure(figsize=(10, 3 * rows))
    axes = fig.subplots(rows, cols, squeeze=False) if rows * cols > 1 else [[plt.gca()]]

    # Initialize fresh buffers
    time_buffer = deque(maxlen=buf_len)
    channel_buffers = [deque(maxlen=buf_len) for _ in range(ch_count)]
    buffers = (time_buffer, channel_buffers)

    # Clear and recreate lines
    lines.clear()
    lines_axes.clear()

    for ch in range(ch_count):
        if ch < rows * cols:
            row = ch // cols
            col = ch % cols
            ax = axes[row][col]
        else:
            ax = axes[0][0]  # Fallback

        ax.clear()
        ax.set_title(stream['ch_labels'][ch], fontsize=10)
        ax.set_xlim(0, plot_duration)

        # Set appropriate Y-limits based on channel type
        ch_label = stream['ch_labels'][ch].upper()
        if "ECG" in ch_label:
            ax.set_ylim(-2000, 2000)  # Microvolts
        elif "HR" in ch_label:
            ax.set_ylim(40, 200)  # BPM
        elif "RRI" in ch_label:
            ax.set_ylim(300, 1500)  # Milliseconds
        elif "ACC" in ch_label:
            ax.set_ylim(-8000, 8000)  # mG
        else:
            ax.set_ylim(-1.5, 1.5)  # Default for unknown data

        ax.grid(True, alpha=0.3)
        line, = ax.plot([], [], linewidth=1)
        lines.append(line)
        lines_axes.append(ax)

    # Remove unused axes
    for idx in range(ch_count, rows * cols):
        row = idx // cols
        col = idx % cols
        if row < len(axes) and col < len(axes[0]):
            fig.delaxes(axes[row][col])

    title = stream.get("display_name", stream['name'])
    fig.suptitle(title, fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    # Create new canvas
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill='both', expand=True)
    canvas.draw()


def on_stream_select():
    if not stream_info:
        return
    stream_name = selected_stream_var.get()
    if stream_name in stream_names:
        idx = stream_names.index(stream_name)
        stop_visualization()  # Stop current visualization
        setup_stream_buffers_and_plots(idx)  # Clean setup
        start_visualization()  # Restart


def update_plot():
    global no_data_counter, frozen_due_to_no_data

    if not visualization_running or not stream_info:
        root.after(int(update_interval * 1000), update_plot)
        return

    stream_name = selected_stream_var.get()
    if stream_name not in stream_names:
        root.after(int(update_interval * 1000), update_plot)
        return

    idx = stream_names.index(stream_name)
    inlet = stream_info[idx]['inlet']
    time_buffer, channel_buffers = buffers

    # Pull ALL available samples to avoid backlog
    samples_pulled = 0
    while True:
        try:
            sample, timestamp = inlet.pull_sample(timeout=0.0)  # Non-blocking
            if sample is None:
                break

            samples_pulled += 1
            now = time.time() - start_time
            time_buffer.append(now)
            for ch, val in enumerate(sample):
                channel_buffers[ch].append(val)

            # Limit to prevent GUI freeze with too many samples
            if samples_pulled > 50:
                break

        except Exception as e:
            break

    if samples_pulled > 0:
        no_data_counter = 0
        frozen_due_to_no_data = False
    else:
        no_data_counter += 1
        if no_data_counter > max_no_data_count and not frozen_due_to_no_data:
            print("No data received; freezing visualization.")
            frozen_due_to_no_data = True

    # Update plot only if we have data - FIXED VERSION
    if len(time_buffer) > 0:
        now = time_buffer[-1] if time_buffer else 0
        x_start = max(0, now - plot_duration)

        for ch in range(len(channel_buffers)):
            if ch < len(lines):
                xdata = list(time_buffer)
                ydata = list(channel_buffers[ch])

                # Filter out NaN values for plotting
                clean_ydata = [y for y in ydata if not math.isnan(y)]
                clean_xdata = [x for i, x in enumerate(xdata) if not math.isnan(ydata[i])]

                if clean_ydata:  # Only plot if we have valid data
                    lines[ch].set_data(clean_xdata, clean_ydata)

                    if ch < len(lines_axes):
                        ax = lines_axes[ch]
                        ax.set_xlim(x_start, max(x_start + 0.1, now))

                        # Safe min/max calculation
                        y_min, y_max = min(clean_ydata), max(clean_ydata)
                        margin = max(0.1, (y_max - y_min) * 0.1)
                        ax.set_ylim(y_min - margin, y_max + margin)
                else:
                    # Reset axis if no valid data
                    lines[ch].set_data([], [])
                    if ch < len(lines_axes):
                        ax = lines_axes[ch]
                        # Reset to appropriate defaults based on channel type
                        ch_label = stream_info[idx]['ch_labels'][ch].upper()
                        if "ECG" in ch_label:
                            ax.set_ylim(-2000, 2000)
                        elif "HR" in ch_label:
                            ax.set_ylim(40, 200)
                        elif "RRI" in ch_label:
                            ax.set_ylim(300, 1500)
                        elif "ACC" in ch_label:
                            ax.set_ylim(-8000, 8000)
                        else:
                            ax.set_ylim(-1, 1)

        try:
            canvas.draw_idle()  # More efficient than canvas.draw()
        except:
            canvas.draw()

    # Use precise timing
    root.after(int(update_interval * 1000), update_plot)


def start_visualization():
    global visualization_running, no_data_counter, frozen_due_to_no_data
    if not visualization_running:
        print("Starting visualization...")
    visualization_running = True
    no_data_counter = 0
    frozen_due_to_no_data = False


def stop_visualization():
    global visualization_running
    if visualization_running:
        print("Pausing visualization...")
    visualization_running = False


def discover_streams_background():
    def worker():
        global stream_info, stream_names

        print("Background: Looking for LSL streams (timeout = 2s)...")
        try:
            streams = resolve_streams(wait_time=2.0)  # blocking call
        except Exception as e:
            print("Error resolving streams:", e)
            streams = []

        new_stream_info = []
        new_stream_names = []

        for stream in streams:
            inlet = StreamInlet(stream)
            info = inlet.info()
            name = info.name()
            hostname = info.hostname()
            uid = info.uid()
            source_id = info.source_id()
            channel_count = info.channel_count()
            srate = int(info.nominal_srate() or sampling_rate_guess)

            # Prefer hostname for readability, but fall back to UID if needed
            if hostname:
                display_name = f"{name} ({hostname})"
            else:
                display_name = f"{name} ({uid[:6]})"  # use short UID if no hostname

            # For absolute uniqueness, include UID at the end (hidden from the dropdown if you want)
            unique_key = f"{display_name} [{uid}]"

            ch_labels = []
            try:
                channels_elem = info.desc().child("channels")
                if not channels_elem.empty():
                    ch_elem = channels_elem.child("channel")
                    while not ch_elem.empty():
                        # Look for labels first, then names, then type as fallbacks
                        channel_label = ch_elem.child_value("label")
                        if channel_label:
                            ch_labels.append(channel_label)
                        else:
                            channel_name = ch_elem.child_value("name")
                            if channel_name:
                                ch_labels.append(channel_name)
                            else:
                                channel_type = ch_elem.child_value("type")
                                if channel_type:
                                    ch_labels.append(channel_type)
                                else:
                                    # Final fallback: use index
                                    ch_labels.append(f"Channel {len(ch_labels) + 1}")

                        ch_elem = ch_elem.next_sibling()
            except Exception as e:
                print(f"Error reading channel info: {e}")
                pass

            # Debug: Print what we found
            print(f"Stream: {name}")
            print(f"Expected channels: {channel_count}")
            print(f"Channel labels/names found: {ch_labels}")

            # If we didn't get the right number of channels, use defaults
            if len(ch_labels) != channel_count:
                print(f"Channel count mismatch. Expected {channel_count}, got {len(ch_labels)}. Using default names.")
                ch_labels = [f"Ch {i + 1}" for i in range(channel_count)]

            new_stream_info.append({
                'name': name,
                'hostname': hostname,
                'uid': uid,
                'source_id': source_id,
                'display_name': display_name,
                'unique_key': unique_key,
                'ch_labels': ch_labels,
                'ch_count': channel_count,
                'srate': srate,
                'inlet': inlet
            })
            new_stream_names.append(unique_key)  # use this for the dropdown values

        if not new_stream_info:
            new_stream_names.append("No Streams Found")

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
                    if new_stream_names and new_stream_names[0] != "No Streams Found":
                        selected_stream_var.set(stream_names[0])
                        if stream_info and visualization_running:
                            setup_stream_buffers_and_plots(0)
                    else:
                        selected_stream_var.set("No Streams Found")
                        if fig:
                            fig.clf()
                            if canvas:
                                canvas.draw()

        root.after(0, update_ui)

    threading.Thread(target=worker, daemon=True).start()


def periodic_discover_streams():
    discover_streams_background()
    root.after(5000, periodic_discover_streams)


# --- GUI Setup ---
root = tk.Tk()
root.title("ÆON Realtime LSL Dashboard")

root.attributes('-fullscreen', False)
style = ttk.Style()
# Dropdown (combobox) style
style.configure("TCombobox",
                font=("Arial", 18),  # font size for entry/displayed text
                padding=10)  # inside padding for height/width
root.option_add("*TCombobox*Listbox.Font", ("Arial", 18))  # font size for the dropdown list items

top_frame = tk.Frame(root)
top_frame.pack(fill='x', padx=10, pady=5)

selected_stream_var = tk.StringVar(value="No Streams Found")
dropdown = ttk.Combobox(top_frame, values=["No Streams Found"], textvariable=selected_stream_var, state="readonly")
dropdown.pack(side='left', fill='x', expand=True, padx=(0, 5))
dropdown.bind("<<ComboboxSelected>>", lambda e: on_stream_select())

btn_font = ("Arial", 12, "bold")
discover_btn = tk.Button(top_frame, text="Discover Streams", font=btn_font, command=discover_streams_background)
discover_btn.pack(side='left', padx=(0, 5))
start_btn = tk.Button(top_frame, text="Start Visualization", font=btn_font, command=start_visualization)
start_btn.pack(side='left', padx=(0, 5))
pause_btn = tk.Button(top_frame, text="Pause Visualization", font=btn_font, command=stop_visualization)
pause_btn.pack(side='left')

discover_btn.config(padx=10, pady=10)
start_btn.config(padx=10, pady=10)
pause_btn.config(padx=10, pady=10)

# Create initial empty figure
fig, axes = plt.subplots(1, 1, figsize=(10, 4))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill='both', expand=True)

# --- Header frame
title_label = tk.Label(root, text="ÆON Realtime LSL Dashboard",
                       font=("Arial", 16, "bold"))
title_label.pack(side="top", pady=5)

# Create a frame inside root (or just below the canvas) to hold logos
logo_frame = tk.Frame(root)
logo_frame.pack(side='bottom', fill='x', padx=10, pady=(0, 5))  # some bottom padding for spacing

# Auburn logo/text (left)
try:
    auburn_logo = tk.PhotoImage(file="auburn_logo.png")
    auburn_logo = auburn_logo.subsample(12, 12)  # shrink by factor (width, height)
    auburn_label = tk.Label(logo_frame, image=auburn_logo)
except Exception:
    auburn_logo = None
    auburn_label = tk.Label(logo_frame, text="Auburn University", font=("Arial", 12, "bold"))

auburn_label.pack(side='left')

# ÆON logo/text (right)
try:
    aeon_logo = tk.PhotoImage(file="aeon_logo.png")
    aeon_logo = aeon_logo.subsample(22, 22)  # shrink by factor (width, height)
    aeon_label = tk.Label(logo_frame, image=aeon_logo)
except Exception:
    aeon_logo = None
    aeon_label = tk.Label(logo_frame, text="ÆON Lab", font=("Arial", 12, "bold"))

aeon_label.pack(side='right')

# Initial discovery at startup
discover_streams_background()

# Start periodic background discovery every 5 seconds
root.after(5000, periodic_discover_streams)

# Start the live update loop
root.after(100, update_plot)

root.mainloop()

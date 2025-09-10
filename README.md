<h1 align="center">Realtime LSL Dashboard</h1>

In Aerospace Human Factors research, we often work with multimodal data streams coming from different sources such as
flight simulators as well as physiological measures such as Heart Rate Variability (HRV) and Eye Tracking.
These data streams are collected in real-time using Lab Streaming Layer (LSL) and are typically recorded using LabRecorder.
Monitoring data quality in real-time is a critical for:  
- Ensuring the correct data streams are being received  
- Verifying channels and sampling rates 
- Avoiding erroneous or missing data

However, there are very few opensource and easy to use tools for realtime monitoring of such multimodal datastreams.

To address this, we developed this Realtime LSL Dashboard, a Python-based, interactive GUI for visualizing multiple LSL streams and channels in real-time. 
This dashboard allows researchers to quickly verify stream integrity and monitor the data quality before or during recording sessions. To allow the users to test this dashboard, we have also provided the code for a dummy stream which includes standard signals.

The dashboard was conceptualized by Dr. Nicoletta Fala (PI of AEON Lab). Md Mijanur Rahman (Graduate Student of AEON Lab) developed the dashboard. We also have future plans to improve the user interface and functionality of this dashboard and will update this repositoty as needed.

## Dashboard Overview
The video below shows the realtime dashboard which is currently displaying the "Dummy Stream".

https://github.com/user-attachments/assets/bee008b8-275e-44bd-a37c-a61ab781b06e

## Features
- **Automatic stream discovery:** Detect available LSL streams in real-time.
- **Multi-channel plotting:** Supports multiple channels per stream with configurable layouts.
- **Interactive controls:** Start, pause, and switch between streams on-the-fly.
- **Dynamic visualization:** Centers plots around the latest data for better real-time monitoring.
- **Stream and channel metadata:** Displays labels for each channel automatically from LSL metadata.
- **Error handling:** Detects missing or frozen streams and notifies the user.
- **Branding support:** Includes placeholders for lab and university logos.

## How to Run

Download the .py file and run in your preferred python IDE. Pip install dependencies if needed.

## Citation

If you use this code for academic work, please cite our repository.

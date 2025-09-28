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
This dashboard allows researchers to quickly verify stream integrity and monitor the data quality before or during recording sessions. To allow the users to test this dashboard, we have also provided the code for a dummy stream which includes standard signals as well as a code for streaming mouse data for realtime data checking.

The dashboard was conceptualized by Dr. Nicoletta Fala (PI of AEON Lab) and developed by Md Mijanur Rahman (Graduate Student of AEON Lab). We also have future plans to improve the user interface and functionality of this dashboard and will update this repositoty as needed.

## Dashboard Overview
The video below shows the realtime dashboard and several streams.

https://github.com/user-attachments/assets/bce1acd1-e2e9-40c9-be45-994506f37838

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

## Changelog

### v2
- Fixed buffer issues for smoother data handling
- Improved UI responsiveness and layout
- Added fallback mechanisms for missing or delayed data
- Enabled compatibility with Polar H10 sensor data
- Introduced new script for streaming mouse data to assist with data quality checks

### v1
- Initial release of the dashboard interface
- Implemented basic dummystream functionality for testing and prototyping

## Citation

If you use this code for academic work, please cite our repository.

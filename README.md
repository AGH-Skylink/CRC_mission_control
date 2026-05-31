# CRC Mission Control

[![Python](https://img.shields.io/badge/Language-Python_3.10+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![DearPyGui](https://img.shields.io/badge/GUI-DearPyGui-red?style=flat-square&logo=python)](https://dearpygui.readthedocs.io/)
[![NumPy](https://img.shields.io/badge/Data-NumPy-013243?style=flat-square&logo=numpy)](https://numpy.org/)
[![Serial](https://img.shields.io/badge/Communication-PySerial-orange?style=flat-square&logo=arduino)](https://pyserial.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**CRC Mission Control** is a high-performance ground station software suite engineered for the AGH-Skylink rocketry team. It provides real-time telemetry monitoring, flight command capabilities, and robust data logging for high-power rocket missions.

---

## 🚀 Overview
Mission Control acts as the central hub between the flight computer and mission operators. By utilizing **DearPyGui**, it delivers an ultra-responsive, GPU-accelerated interface capable of rendering complex flight data and 3D orientation in real-time without straining system resources.

## ✨ Key Features

### 📡 Real-Time Telemetry & Monitoring
* **High-Frequency Data Parsing**: Efficiently decodes 50-byte binary telemetry frames using custom struct packing.
* **Live Status Dashboard**: Monitors critical flight parameters: altitude, temperature, battery voltage, and RSSI with intelligent alert thresholds.
* **Connection Health**: Advanced Link Quality monitoring with automated detection of dropped frames and signal loss.

### 🧭 Advanced Flight Visualization
* **Custom Navball Widget**: A high-fidelity, GPU-drawn attitude indicator showing real-time Pitch, Roll, and Yaw.
* **Trajectory Tracking**: Live map and path visualization using integrated graphing tools to track flight descent and landing recovery.

### 🛠️ Command & Control
* **Macro Sequence Engine**: Easily configure and execute automated pre-flight, launch, and abort procedures.
* **Hardware Interface**: Dedicated control panels for monitoring sensors (IMU, Barometer) and testing pyrotechnic recovery hardware.

### 💾 Data Integrity & Analysis
* **Triple-Layer Logging**: Simultaneous logging of system events, CSV-formatted telemetry data, and raw binary frames for post-flight analysis.
* **Flight Replayer**: Integrated tools to load and replay mission logs, allowing for "what-if" analysis and debriefing.

---

## 🏗️ Technical Architecture

The application follows a modular architecture designed for maintainability and scalability:

* **Core**: Handles high-speed serial communication (`SerialManager`), binary telemetry deserialization (`TelemetryParser`), and state machine management.
* **UI**: A reactive layer built on `DearPyGui`, featuring custom themes (`theme.py`), modular components, and complex widgets.
* **Logging**: A custom logging system that ensures mission-critical data is captured instantly, even in the event of interface crashes.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* `pip`

### Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/AGH-Skylink/CRC_mission_control
   cd CRC_mission_control
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   python main.py
   ```
---

## 👨‍💻 Project Authorship
This mission control panel was developed by **[Dobrawa Rumszewicz](https://github.com/tsuruguu)** for the **Czech Rocket Challenge** as part of the **[AGH-Skylink](https://github.com/AGH-Skylink)** scientific society.

*   **GitHub**: [tsuruguu](https://github.com/tsuruguu)
*   **LinkedIn**: [Dobrawa Rumszewicz](https://www.linkedin.com/in/dobrawa-rumszewicz/)

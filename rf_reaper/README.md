# ⚡ RF-REAPER

### Unified 2.4GHz Attack Platform

> **$3 hardware. $0 software. Infinite possibilities.**

RF-Reaper combines the capabilities of **MouseJack**, **LOGITacker**, **KeySweeper**, and **Flipper Zero's nRF24 module** into a single, open-source toolkit with a stunning cyberpunk web dashboard.

![License](https://img.shields.io/badge/license-MIT-cyan)
![Platform](https://img.shields.io/badge/platform-Linux-green)
![Hardware](https://img.shields.io/badge/hardware-$3-magenta)

---

## 🔥 Why RF-Reaper?

| Tool | Hardware Required | Cost | RF-Reaper? |
|---|---|---|---|
| MouseJack | CrazyRadio PA (nRF24LU1+) | ~$30 | ✅ Included |
| LOGITacker | Nordic nRF52840 Dongle | ~$10 | ✅ Included |
| KeySweeper | Arduino + nRF24L01 | ~$15 | ✅ Included |
| Flipper Zero + nRF24 | Flipper Zero + GPIO module | ~$200+ | ✅ Included |
| **RF-Reaper** | **Arduino Nano + nRF24L01+** | **$3** | **ALL IN ONE** |

## 🛠️ Hardware Setup

### Required ($3 total)
```
Arduino Nano Clone .............. $2
nRF24L01+ Module ................ $1
5 Dupont Wires .................. $0 (usually included)
```

### Wiring
```
nRF24L01+    →    Arduino Nano
─────────────────────────────────
VCC (3.3V)   →    3.3V
GND          →    GND
CE           →    Pin 9
CSN          →    Pin 10
SCK          →    Pin 13
MOSI         →    Pin 11
MISO         →    Pin 12
IRQ          →    (not connected)
```

### Optional
- **YICHIP USB Dongle** — For passive 2.4GHz monitoring (our original research target)

## ⚡ Features

### 📡 Scanner — 2.4GHz Spectrum Analyzer
- Sweep all 126 channels (2400-2525 MHz)
- Visual spectrum display with signal strength per channel
- Automatic device detection and profiling
- Configurable dwell time per channel

### 🔍 Sniffer — Packet Capture & Decode
- Promiscuous mode packet capture
- Real-time HID packet decoding (keyboard + mouse)
- Address and channel filtering
- Microsoft keyboard decryption (KeySweeper capability)
- Packet statistics and device profiling

### 💉 Injector — Keystroke & Mouse Injection
- **DuckyScript support** — Full USB Rubber Ducky script compatibility
- **Text injection** — Type any text on the target
- **Mouse injection** — Move cursor, click buttons
- **Preset payloads** — Reverse shell, data exfil, rickroll, etc.
- Target by address + channel

### 🎯 Tracker — Device Following
- Lock onto a specific device address
- Real-time signal strength monitoring
- Channel hop tracking
- Movement pattern visualization (mouse)
- Keystroke logging (keyboard)

### 🔓 YICHIP Analysis — Dongle Research
- First-ever YICHIP (VID 0x3151) reverse engineering toolkit
- HID descriptor parsing and vendor channel discovery
- USB control transfer fuzzing
- Serial number extraction
- Vendor command probing

## 🚀 Quick Start

### 1. Flash the Arduino
```bash
# Open rf_reaper/firmware/rf_reaper_firmware.ino in Arduino IDE
# Select Board: Arduino Nano
# Select Port: /dev/ttyUSB0 (or equivalent)
# Upload
```

### 2. Install dependencies
```bash
pip3 install pyserial
```

### 3. Launch RF-Reaper
```bash
cd rf_reaper
python3 rf_reaper.py
```

### 4. Open Dashboard
```
http://localhost:8670
```

## 🎨 Dashboard

The RF-Reaper dashboard is a cyberpunk-themed web interface featuring:
- Real-time spectrum analyzer visualization
- Live packet capture and decoding
- DuckyScript injection console
- Device tracking with signal strength
- YICHIP dongle analysis panel
- Terminal-style console log

## 📁 Project Structure

```
rf_reaper/
├── rf_reaper.py              # Python backend (API + serial + SSE)
├── dashboard.html            # Cyberpunk web dashboard
├── firmware/
│   ├── rf_reaper_firmware.ino  # Arduino firmware
│   └── protocol.md            # Serial protocol documentation
├── yichip/                     # YICHIP dongle tools
│   ├── cracker.py              # USB-level analysis
│   ├── deep_probe.py           # HID vendor channel probe
│   ├── sniffer.py              # Passive monitoring
│   └── cracker_results.json    # Research findings
└── README.md
```

## ⚠️ Legal Disclaimer

**This tool is for authorized security research and educational purposes ONLY.**

- Only use on devices you own or have explicit permission to test
- Unauthorized interception of wireless communications is illegal
- Keystroke injection on unauthorized systems is illegal
- The authors are not responsible for misuse

## 🪦 Origin Story

A wireless mouse was lost in Spain 🇪🇸. Its orphaned USB dongle remained behind. Instead of throwing it away, we decided to reverse-engineer it and build something that nobody had built before.

The YICHIP dongle couldn't be repurposed — but the research led us to create RF-Reaper: a unified 2.4GHz attack platform that replaces $200+ worth of specialized hardware with a $3 Arduino + nRF24L01+ setup.

**The mouse died so RF-Reaper could live.**

## 📜 License

MIT — Free as in freedom, free as in beer.

---

<p align="center">
  <b>⚡ RF-REAPER ⚡</b><br>
  <i>"$3 hardware. $0 software. Infinite possibilities."</i>
</p>

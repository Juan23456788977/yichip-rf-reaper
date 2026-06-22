# 🔓 yichip-dongle-toolkit

**First-ever open-source YICHIP USB dongle analysis & reverse engineering toolkit.**

> Nobody has published YICHIP dongle research before. This is the first.

## 🎯 What is this?

A collection of Python tools for analyzing, reverse engineering, and probing **YICHIP** wireless USB dongles (VID `0x3151`). These are the cheap 2.4GHz receivers found in generic Chinese wireless mice and keyboards.

When you lose the mouse but keep the dongle, most people throw it away. We decided to crack it open instead.

## 🔬 Findings

### Device Profile

| Property | Value |
|---|---|
| Vendor ID | `0x3151` (YICHIP) |
| Product ID | `0x3000` |
| Probable Chip | **YC1021** — 32-bit RISC SoC, triple-mode (BT 3.0/4.x/5.0 + 2.4GHz) |
| USB Version | 2.0 |
| Interfaces | 2 × HID (Keyboard + Mouse) |
| Serial Number | `b120300001` |
| Power | 100mA (bus powered) |

### Hidden Vendor Channels (Undocumented)

The dongle exposes **two hidden vendor-specific HID channels** that are not part of the standard keyboard/mouse interface:

#### Channel 1: Report ID `0xBA` (Usage Page `0xFF00`)
- **Direction:** Bidirectional (Input + Output)
- **Size:** 31 bytes per report
- **SET_REPORT:** ✅ Accepted (chip receives data)
- **GET_REPORT:** Returns zeros (chip doesn't respond via control transfer)
- **Interrupt Endpoint:** Needs further investigation

#### Channel 2: Report ID `0x04` (Usage Page `0xFFBC`)
- **Direction:** Input only
- **Size:** 1 byte
- **Purpose:** Unknown vendor-specific data

### USB Analysis Results

| Test | Result |
|---|---|
| String Descriptors (0-255) | 3 found: "YICHIP", "Wireless Device", **"b120300001"** (serial) |
| Vendor USB Requests (0xC0) | All rejected (STALL) |
| HID GET_REPORT (all types) | Report 0xBA returns zeros |
| HID SET_REPORT (Output) | ✅ **Accepted for 0xBA and 0x04** |
| HID SET_REPORT (Feature) | ✅ **Accepted for 0xBA and 0x04** |
| DFU Bootloader | DETACH rejected |
| Bootloader magic sequences | All rejected |
| Physical Descriptor | Exists on interface 1 |
| Vendor channel brute force | 289 command combinations, 0 responses via GET_REPORT |

### Serial Number Analysis

The serial `b120300001` appears to encode:
- `b` — Batch/board prefix
- `1203` — Possible firmware version (v12.03) or date (2012-03)
- `00001` — Unit number
- As possible RF address: `0xB1 0x20 0x30 0x00 0x01`

### Key Insight

The chip **accepts all SET_REPORT commands** on the vendor channel but **never responds via GET_REPORT**. This suggests either:
1. Responses come through the **interrupt endpoint** (not tested with proper synchronization yet)
2. The vendor channel is **write-only** from the host perspective
3. The correct command **magic bytes** haven't been found yet

## 🛠️ Tools Included

### `cracker.py` — USB Deep Analysis (v1.0)
Full USB-level analysis with 7 phases:
1. USB Deep Enumeration (string descriptors, BOS, device qualifier)
2. USB Control Transfer Fuzzing (vendor, class, standard requests)
3. DFU/Bootloader Discovery
4. HID Feature Report Deep Scan (256 report IDs × 2 interfaces)
5. SET_REPORT Injection
6. Vendor Channel Brute Force (289 combinations)
7. USB Configuration Analysis

```bash
sudo python3 cracker.py
```

### `deep_probe.py` — HID Vendor Channel Probe
Sends 75+ commands through the hidden Report ID 0xBA channel via hidraw:
- Standard RF chip commands (GET_VERSION, PAIR_MODE, etc.)
- YICHIP-specific magic sequences (0x55AA, 0xAA55, etc.)
- Vendor Page 0xFFBC probing
- Brute force scan (commands 0x00-0x30)

```bash
sudo chmod 666 /dev/hidraw2
python3 deep_probe.py
```

### `yichip_sniffer.py` — Live Packet Monitor
Real-time monitoring of the dongle's HID interrupt endpoints:
- Watches for any RF signal from paired devices
- Decodes mouse movement, button presses, keyboard events
- Safe: only monitors YICHIP hidraw devices

```bash
sudo chmod 444 /dev/hidraw0 /dev/hidraw2
python3 yichip_sniffer.py
```

### `server.py` + `dashboard.html` — Hacking Dashboard
Web-based cyberpunk dashboard with:
- Real-time radar visualization
- Live packet monitor
- HID descriptor reverse engineering viewer
- Vendor command probe interface
- Vulnerability scanner

```bash
sudo chmod 444 /dev/hidraw0 /dev/hidraw2
python3 server.py
# Open http://localhost:8666
```

## ⚠️ Prerequisites

```bash
pip3 install pyusb
# Also need: libusb (usually pre-installed on Linux)
```

## 🔍 Identifying Your Dongle

```bash
lsusb | grep 3151
# Bus 002 Device 005: ID 3151:3000 YICHIP Wireless Device
```

## 📊 Raw HID Descriptors

<details>
<summary>Interface 0 — Keyboard (63 bytes)</summary>

```
05 01 09 06 a1 01 75 01 95 08 05 07 19 e0 29 e7
15 00 25 01 81 02 95 01 75 08 81 03 95 05 75 01
05 08 19 01 29 05 91 02 95 01 75 03 91 03 95 06
75 08 15 00 25 ff 05 07 19 00 29 ff 81 00 c0
```

Standard 6KRO keyboard with 5 LED outputs.
</details>

<details>
<summary>Interface 1 — Mouse + Vendor (195 bytes)</summary>

```
05 01 09 02 a1 01 85 01 09 01 a1 00 05 09 19 01
29 05 15 00 25 01 95 05 75 01 81 02 95 01 75 03
81 01 05 01 09 30 09 31 16 01 f8 26 ff 07 75 10
95 02 81 06 09 38 15 81 25 7f 75 08 95 01 81 06
05 0c 0a 38 02 95 01 81 06 c0 c0 05 01 09 80 a1
01 85 02 05 01 19 81 29 83 15 00 25 01 95 03 75
01 81 06 95 01 75 05 81 01 c0 05 0c 09 01 a1 01
85 03 15 00 26 80 03 19 00 2a 80 03 75 10 95 01
81 00 c0 06 bc ff 09 88 a1 01 85 04 19 00 2a ff
00 15 00 26 ff 00 75 08 95 01 81 00 c0 06 00 ff
09 0e a1 01 85 ba 95 1f 75 08 26 ff 00 15 00 09
01 91 02 85 ba 95 1f 75 08 26 ff 00 15 00 09 01
81 02 c0
```

Contains: 5-button mouse (16-bit X/Y), system control, consumer control, **Vendor Page 0xFFBC (Report 0x04)**, **Vendor Page 0xFF00 (Report 0xBA, 31 bytes bidirectional)**.
</details>

## 🤝 Contributing

This is uncharted territory. If you have a YICHIP dongle and want to help:

1. Run `cracker.py` and share your results
2. Try different YICHIP product IDs (0x3020, etc.)
3. If you have a J-Link/SWD debugger, try connecting to the YC1021's debug pins
4. If you have the YICHIP SDK, help us understand the vendor protocol

## 📜 License

MIT — Use for educational and authorized security research only.

## 🪦 Backstory

A mouse was lost in Spain. Its orphaned dongle remained. Instead of throwing it away, we decided to become the first people to reverse-engineer a YICHIP USB dongle. This repository is the result.

*RIP Mouse 🐭 — somewhere in España 🇪🇸*

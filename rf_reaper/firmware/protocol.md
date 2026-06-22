# RF-Reaper Serial Protocol v1.0

Communication between the Python host and the Arduino firmware uses JSON over serial at **115200 baud**.

## Message Format

### Host → Arduino (Commands)
```json
{"cmd": "<command>", "params": {<parameters>}}
```

### Arduino → Host (Responses)
```json
{"type": "<response_type>", <data fields>}
```

---

## Commands

### System

| Command | Params | Description |
|---------|--------|-------------|
| `ping` | — | Handshake. Returns firmware version |
| `status` | — | Get current mode, channel, register states |
| `stop` | — | Stop current operation, return to idle |
| `set_channel` | `channel` (0-125) | Set RF channel |
| `set_rate` | `rate` (250, 1000, 2000) | Set data rate in kbps |
| `read_reg` | `reg` (0-29) | Read nRF24L01+ register |

### Scanner

| Command | Params | Description |
|---------|--------|-------------|
| `scan` | `dwell` (1-100ms) | Sweep all 126 channels, report signal strength |

### Sniffer

| Command | Params | Description |
|---------|--------|-------------|
| `sniff` | `channel` (0=hop), `address` (optional, "AA:BB:CC:DD:EE") | Start packet capture. No address = promiscuous mode |

### Injector

| Command | Params | Description |
|---------|--------|-------------|
| `inject_key` | `address`, `channel`, `modifier` (0-255), `key` (HID keycode) | Inject single keystroke |
| `inject_mouse` | `address`, `channel`, `x` (-128..127), `y` (-128..127), `buttons` (bitmask) | Inject mouse movement |
| `inject_raw` | `address`, `channel`, `raw` (hex string) | Inject raw payload bytes |
| `inject_sequence` | `address`, `channel` | Prepare TX for sequence (then send individual inject_key) |

### Tracker

| Command | Params | Description |
|---------|--------|-------------|
| `follow` | `address` ("AA:BB:CC:DD:EE") | Lock onto device, capture all traffic |

### Jammer

| Command | Params | Description |
|---------|--------|-------------|
| `jam` | `channel` (0-125) | Continuous noise on channel |

---

## Response Types

| Type | Fields | When |
|------|--------|------|
| `pong` | `fw`, `hw` | Reply to `ping` |
| `boot` | `fw`, `hw`, `pins` | Firmware startup |
| `debug` | `msg` | Status/info messages |
| `error` | `msg` | Error messages |
| `scan_complete` | `sweep`, `data` (126-element array) | After full channel sweep |
| `scan_result` | `ch`, `strength`, `freq` | Individual hot channel |
| `packet` | `ch`, `pipe`, `len`, `raw` (hex), `addr` | Captured packet |
| `inject_ok` | `bytes` or `key`/`mouse` | Successful injection |
| `inject_fail` | `error` | Failed injection |
| `status` | `mode`, `status`, `config`, `channel`, `rf_setup` | Register dump |
| `reg` | `reg`, `val` | Single register read |

---

## Examples

### Start scanning
```json
→ {"cmd":"scan","params":{"dwell":2}}
← {"type":"debug","msg":"Scan started, dwell=2ms"}
← {"type":"scan_result","ch":42,"strength":3,"freq":2442}
← {"type":"scan_complete","sweep":1,"data":[0,0,0,...,3,...,0]}
```

### Sniff promiscuous on channel 42
```json
→ {"cmd":"sniff","params":{"channel":42}}
← {"type":"debug","msg":"Sniffing ch42 promiscuous"}
← {"type":"packet","ch":42,"pipe":0,"len":32,"raw":"0A00BB...","addr":"0A:00:BB:CC:DD"}
```

### Inject keystroke (type 'a' on target)
```json
→ {"cmd":"inject_key","params":{"address":"BB:0A:DC:A5:75","channel":42,"modifier":0,"key":4}}
← {"type":"inject_ok","key":true}
```

### Inject DuckyScript (via host sequence)
```json
→ {"cmd":"inject_sequence","params":{"address":"BB:0A:DC:A5:75","channel":42}}
← {"type":"debug","msg":"TX ready on ch42, send inject_key commands"}
→ {"cmd":"inject_key","params":{"address":"BB:0A:DC:A5:75","channel":42,"modifier":8,"key":21}}
← {"type":"inject_ok","key":true}
```

---

## Addressing

- Addresses are 5 bytes in `AA:BB:CC:DD:EE` hex format
- Promiscuous mode uses 3-byte address `AA:00:00` internally
- Logitech Unifying addresses typically start with `BB:`

## Data Rates

| Rate | Common Usage |
|------|-------------|
| 2 Mbps | Logitech Unifying, most wireless mice |
| 1 Mbps | Some keyboards, Microsoft devices |
| 250 kbps | Long range, some industrial devices |

## Channels

- **0-125** maps to **2400-2525 MHz**
- Most wireless mice use channels **2-80**
- Bluetooth overlaps **2-79**
- WiFi channels 1/6/11 overlap heavily

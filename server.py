#!/usr/bin/env python3
"""
YICHIP HACKING DASHBOARD - Backend
===================================
Servidor web con Server-Sent Events para monitoreo en tiempo real
del dongle YICHIP. Incluye análisis forense HID, sniffing de paquetes,
e intento de modo pairing.

SEGURO: Solo toca hidraw0 y hidraw2 (YICHIP)
NO TOCA: hidraw1 (mouse JVC), hidraw4/5 (teclado Logitech)
"""

import http.server
import json
import os
import select
import struct
import fcntl
import threading
import time
import queue
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURACIÓN - SOLO DISPOSITIVOS YICHIP
# ============================================================
YICHIP_DEVICES = {
    '/dev/hidraw0': {'name': 'YICHIP-Keyboard', 'interface': 'keyboard'},
    '/dev/hidraw2': {'name': 'YICHIP-Mouse', 'interface': 'mouse'},
}

PORT = 8666
event_queue = queue.Queue()
packet_log = []
dongle_info = {}

# ============================================================
# ANÁLISIS FORENSE HID
# ============================================================
def parse_hid_descriptor(raw_bytes):
    """Parsea los bytes del descriptor HID a campos legibles"""
    items = []
    i = 0
    
    USAGE_PAGES = {
        0x01: 'Generic Desktop', 0x05: 'Game Controls',
        0x07: 'Keyboard/Keypad', 0x08: 'LED',
        0x09: 'Button', 0x0C: 'Consumer',
        0x0D: 'Digitizers', 0xFF00: 'Vendor-Defined',
        0xFFBC: '⚠️ VENDOR SPECIFIC (0xFFBC)',
    }
    
    USAGES_DESKTOP = {
        0x01: 'Pointer', 0x02: 'Mouse', 0x04: 'Joystick',
        0x06: 'Keyboard', 0x30: 'X', 0x31: 'Y',
        0x38: 'Wheel', 0x80: 'System Control',
    }
    
    MAIN_TAGS = {
        0x80: 'Input', 0x90: 'Output', 0xA0: 'Collection',
        0xB0: 'Feature', 0xC0: 'End Collection',
    }
    
    COLLECTION_TYPES = {
        0x00: 'Physical', 0x01: 'Application',
        0x02: 'Logical', 0x03: 'Report',
    }
    
    while i < len(raw_bytes):
        byte = raw_bytes[i]
        
        if byte == 0xFE:  # Long item
            if i + 2 < len(raw_bytes):
                data_size = raw_bytes[i + 1]
                i += 3 + data_size
            continue
        
        bSize = byte & 0x03
        if bSize == 3:
            bSize = 4
        bType = (byte >> 2) & 0x03
        bTag = (byte >> 4) & 0x0F
        
        data = raw_bytes[i+1:i+1+bSize] if bSize > 0 else b''
        value = int.from_bytes(data, 'little', signed=False) if data else 0
        
        item = {
            'offset': i,
            'raw': ' '.join(f'{b:02x}' for b in raw_bytes[i:i+1+bSize]),
            'type': ['Main', 'Global', 'Local', 'Reserved'][bType],
            'tag': bTag,
            'value': value,
            'size': bSize,
        }
        
        # Decode meaning
        if bType == 1:  # Global
            if bTag == 0: item['meaning'] = f'Usage Page: {USAGE_PAGES.get(value, f"0x{value:04X}")}'
            elif bTag == 1: item['meaning'] = f'Logical Minimum: {value}'
            elif bTag == 2: item['meaning'] = f'Logical Maximum: {value}'
            elif bTag == 3: item['meaning'] = f'Physical Minimum: {value}'
            elif bTag == 4: item['meaning'] = f'Physical Maximum: {value}'
            elif bTag == 7: item['meaning'] = f'Report Size: {value} bits'
            elif bTag == 8: item['meaning'] = f'Report Count: {value}'
            elif bTag == 9: item['meaning'] = f'Report ID: {value}'
        elif bType == 2:  # Local
            if bTag == 0: item['meaning'] = f'Usage: {USAGES_DESKTOP.get(value, f"0x{value:02X}")}'
            elif bTag == 1: item['meaning'] = f'Usage Minimum: 0x{value:02X}'
            elif bTag == 2: item['meaning'] = f'Usage Maximum: 0x{value:02X}'
        elif bType == 0:  # Main
            tag_full = byte & 0xFC
            tag_name = MAIN_TAGS.get(tag_full, f'Unknown(0x{tag_full:02X})')
            if tag_full == 0xA0:
                item['meaning'] = f'Collection: {COLLECTION_TYPES.get(value, f"0x{value:02X}")}'
            elif tag_full == 0xC0:
                item['meaning'] = 'End Collection'
            else:
                flags = []
                if value & 0x01: flags.append('Constant')
                else: flags.append('Data')
                if value & 0x02: flags.append('Variable')
                else: flags.append('Array')
                if value & 0x04: flags.append('Relative')
                else: flags.append('Absolute')
                item['meaning'] = f'{tag_name}: {", ".join(flags)}'
        
        if 'meaning' not in item:
            item['meaning'] = f'Type={item["type"]} Tag={bTag} Value={value}'
        
        items.append(item)
        i += 1 + bSize
    
    return items

def get_hid_descriptors():
    """Lee los descriptores HID del dongle YICHIP"""
    results = {}
    for dev_path, dev_info in YICHIP_DEVICES.items():
        try:
            fd = os.open(dev_path, os.O_RDONLY)
            buf = bytearray(4)
            fcntl.ioctl(fd, 0x80044801, buf)
            size = struct.unpack('I', buf)[0]
            
            desc_buf = bytearray(4 + 4096)
            struct.pack_into('I', desc_buf, 0, size)
            fcntl.ioctl(fd, 0x90044802, desc_buf)
            descriptor = bytes(desc_buf[4:4+size])
            os.close(fd)
            
            parsed = parse_hid_descriptor(descriptor)
            
            # Check for vendor-specific features
            vendor_features = [item for item in parsed 
                             if 'VENDOR' in item.get('meaning', '').upper() 
                             or 'ff' in item.get('raw', '').lower()[:5]]
            
            results[dev_info['name']] = {
                'path': dev_path,
                'descriptor_size': size,
                'raw_hex': ' '.join(f'{b:02x}' for b in descriptor),
                'parsed_items': parsed,
                'vendor_features': vendor_features,
                'has_vendor_channel': len(vendor_features) > 0,
            }
        except Exception as e:
            results[dev_info['name']] = {'error': str(e)}
    
    return results

def analyze_dongle():
    """Análisis completo del dongle"""
    info = {
        'vendor_id': '3151',
        'product_id': '3000',
        'manufacturer': 'YICHIP',
        'product': 'Wireless Device',
        'usb_version': '2.0',
        'interfaces': [],
        'descriptors': get_hid_descriptors(),
        'capabilities': [],
        'vulnerabilities': [],
        'timestamp': datetime.now().isoformat(),
    }
    
    # Analyze capabilities
    mouse_desc = info['descriptors'].get('YICHIP-Mouse', {})
    if mouse_desc.get('has_vendor_channel'):
        info['capabilities'].append({
            'name': 'Vendor-Specific HID Channel',
            'description': 'Report ID 0xBA con 31 bytes — canal de comunicación bidireccional con el chip',
            'danger_level': 'high',
            'icon': '🔓'
        })
        info['capabilities'].append({
            'name': 'Vendor Page 0xFFBC (Report ID 0x04)',
            'description': 'Canal vendor adicional — posible configuración/firmware',
            'danger_level': 'medium',
            'icon': '⚡'
        })
    
    info['capabilities'].append({
        'name': 'Dual HID Interface',
        'description': 'Keyboard + Mouse simultáneo — permite inyección de teclas',
        'danger_level': 'high',
        'icon': '⌨️'
    })
    
    # Vulnerabilities
    info['vulnerabilities'].append({
        'name': 'No cifrado RF',
        'description': 'Comunicación 2.4GHz sin cifrado — vulnerable a sniffing',
        'severity': 'HIGH',
        'cve_like': 'MouseJack-class'
    })
    info['vulnerabilities'].append({
        'name': 'Vendor HID bidireccional',
        'description': 'Canal oculto Report ID 0xBA permite enviar comandos al chip',
        'severity': 'MEDIUM',
        'cve_like': 'HID-Injection'
    })
    
    return info

# ============================================================
# PACKET SNIFFER
# ============================================================
def packet_sniffer_thread():
    """Thread que monitorea paquetes del dongle"""
    fds = {}
    for dev_path, dev_info in YICHIP_DEVICES.items():
        try:
            fd = os.open(dev_path, os.O_RDONLY | os.O_NONBLOCK)
            fds[fd] = dev_info
        except Exception as e:
            event_queue.put({
                'type': 'error',
                'message': f'Error abriendo {dev_path}: {e}'
            })
            return
    
    poll = select.poll()
    for fd in fds:
        poll.register(fd, select.POLLIN)
    
    event_queue.put({'type': 'sniffer_started', 'devices': len(fds)})
    
    count = 0
    while True:
        events = poll.poll(500)
        for fd, event in events:
            if event & select.POLLIN:
                try:
                    data = os.read(fd, 64)
                    if data:
                        count += 1
                        dev_info = fds[fd]
                        packet = {
                            'type': 'packet',
                            'id': count,
                            'device': dev_info['name'],
                            'interface': dev_info['interface'],
                            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
                            'raw': ' '.join(f'{b:02x}' for b in data),
                            'length': len(data),
                            'data': list(data),
                        }
                        
                        # Analyze packet
                        if dev_info['interface'] == 'mouse' and len(data) >= 5:
                            report_id = data[0]
                            packet['report_id'] = report_id
                            if report_id == 1:
                                buttons = data[1]
                                x = struct.unpack('<h', data[2:4])[0]
                                y = struct.unpack('<h', data[4:6])[0]
                                packet['analysis'] = {
                                    'buttons': buttons,
                                    'x': x, 'y': y,
                                    'description': f'Mouse move X={x} Y={y} Buttons={buttons:#04x}'
                                }
                            elif report_id == 0xBA:
                                packet['analysis'] = {
                                    'description': '⚠️ VENDOR COMMAND DETECTED!'
                                }
                        elif dev_info['interface'] == 'keyboard' and len(data) >= 3:
                            modifier = data[0]
                            keys = [b for b in data[2:] if b != 0]
                            packet['analysis'] = {
                                'modifier': modifier,
                                'keys': keys,
                                'description': f'Keyboard mod={modifier:#04x} keys={keys}'
                            }
                        
                        packet_log.append(packet)
                        event_queue.put(packet)
                except OSError:
                    pass
        
        # Send heartbeat
        event_queue.put({
            'type': 'heartbeat',
            'packets': count,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
        })
        time.sleep(0.5)

# ============================================================
# VENDOR COMMAND PROBE
# ============================================================
def try_vendor_commands():
    """Intenta enviar comandos vendor al dongle via Report ID 0xBA"""
    results = []
    dev_path = '/dev/hidraw2'
    
    try:
        fd = os.open(dev_path, os.O_RDWR | os.O_NONBLOCK)
        
        # Comandos comunes de chips 2.4GHz para pairing/config
        probe_commands = [
            {'name': 'GET_VERSION', 'data': bytes([0xBA, 0x01] + [0]*30)},
            {'name': 'GET_STATUS', 'data': bytes([0xBA, 0x02] + [0]*30)},
            {'name': 'GET_CONFIG', 'data': bytes([0xBA, 0x03] + [0]*30)},
            {'name': 'PAIR_MODE', 'data': bytes([0xBA, 0x04] + [0]*30)},
            {'name': 'GET_ADDR', 'data': bytes([0xBA, 0x05] + [0]*30)},
            {'name': 'PING', 'data': bytes([0xBA, 0xFF] + [0]*30)},
        ]
        
        for cmd in probe_commands:
            try:
                os.write(fd, cmd['data'])
                time.sleep(0.1)
                
                try:
                    response = os.read(fd, 64)
                    results.append({
                        'command': cmd['name'],
                        'sent': ' '.join(f'{b:02x}' for b in cmd['data'][:8]) + '...',
                        'response': ' '.join(f'{b:02x}' for b in response),
                        'status': 'RESPONSE',
                        'length': len(response),
                    })
                except (OSError, BlockingIOError):
                    results.append({
                        'command': cmd['name'],
                        'sent': ' '.join(f'{b:02x}' for b in cmd['data'][:8]) + '...',
                        'response': None,
                        'status': 'NO_RESPONSE',
                    })
            except OSError as e:
                results.append({
                    'command': cmd['name'],
                    'status': 'WRITE_ERROR',
                    'error': str(e),
                })
        
        os.close(fd)
    except PermissionError:
        results.append({'command': 'ALL', 'status': 'PERMISSION_DENIED', 
                       'error': 'Need write permission: sudo chmod 666 /dev/hidraw2'})
    except Exception as e:
        results.append({'command': 'ALL', 'status': 'ERROR', 'error': str(e)})
    
    return results

# ============================================================
# HTTP SERVER
# ============================================================
class HackDashboardHandler(http.server.SimpleHTTPRequestHandler):
    
    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html_path = Path(__file__).parent / 'dashboard.html'
            self.wfile.write(html_path.read_bytes())
        
        elif self.path == '/api/info':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(dongle_info, default=str).encode())
        
        elif self.path == '/api/probe':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            results = try_vendor_commands()
            self.wfile.write(json.dumps(results, default=str).encode())
        
        elif self.path == '/api/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                while True:
                    try:
                        event = event_queue.get(timeout=2)
                        data = json.dumps(event, default=str)
                        self.wfile.write(f'data: {data}\n\n'.encode())
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b': keepalive\n\n')
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        
        elif self.path == '/api/packets':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(packet_log[-100:], default=str).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

def main():
    global dongle_info
    
    print("=" * 60)
    print("🔥 YICHIP HACKING DASHBOARD")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Análisis forense
    print("🔬 Analizando dongle...")
    dongle_info = analyze_dongle()
    
    mouse_desc = dongle_info['descriptors'].get('YICHIP-Mouse', {})
    if mouse_desc.get('has_vendor_channel'):
        print("🔓 ¡Canal vendor encontrado! Report ID 0xBA")
        print("⚡ Vendor Page 0xFFBC detectada")
    
    print(f"📋 {len(dongle_info['capabilities'])} capacidades detectadas")
    print(f"⚠️  {len(dongle_info['vulnerabilities'])} vulnerabilidades")
    print()
    
    # Iniciar sniffer
    print("📡 Iniciando sniffer de paquetes...")
    sniffer = threading.Thread(target=packet_sniffer_thread, daemon=True)
    sniffer.start()
    
    # Iniciar servidor web
    print(f"🌐 Dashboard: http://localhost:{PORT}")
    print(f"   Abre este URL en tu navegador")
    print()
    print("⚠️  SOLO monitorea hidraw0/hidraw2 (YICHIP)")
    print("✅ Tu mouse y teclado están SEGUROS")
    print("=" * 60)
    
    server = http.server.HTTPServer(('0.0.0.0', PORT), HackDashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard detenido")
        server.shutdown()

if __name__ == '__main__':
    main()

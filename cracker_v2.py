#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  YICHIP DONGLE CRACKER v2.0 — INTERRUPT ENDPOINT ATTACK         ║
║  El chip ACEPTA SET_REPORT → leemos respuesta por INTERRUPT      ║
║  NADIE ha probado esto antes.                                    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import usb.core
import usb.util
import os
import sys
import time
import json
import struct
import select
import fcntl
from datetime import datetime

VENDOR_ID = 0x3151
PRODUCT_ID = 0x3000
HIDRAW_MOUSE = '/dev/hidraw2'
HIDRAW_KBD = '/dev/hidraw0'

RESULTS = []
DISCOVERIES = []

def log(level, msg, data=None):
    icons = {'INFO': '📋', 'OK': '✅', 'FAIL': '❌', 'WARN': '⚠️', 
             'FOUND': '🔴', 'PROBE': '🔍', 'FIRE': '🔥'}
    icon = icons.get(level, '  ')
    print(f"  {icon} {msg}")
    if data:
        if isinstance(data, (bytes, bytearray, list)):
            if isinstance(data, list):
                data = bytes(data)
            hex_str = ' '.join(f'{b:02x}' for b in data)
            print(f"     → [{len(data)} bytes] {hex_str}")
        else:
            print(f"     → {data}")
    
    entry = {'level': level, 'message': msg, 
             'data': data.hex() if isinstance(data, (bytes, bytearray)) else str(data) if data else None}
    RESULTS.append(entry)
    if level in ('FOUND', 'FIRE'):
        DISCOVERIES.append(entry)

def phase_banner(num, title):
    print(f"\n{'═' * 65}")
    print(f"  FASE {num}: {title}")
    print(f"{'═' * 65}")

# ================================================================
# FASE A: SET_REPORT por USB → leer INTERRUPT por hidraw
# ================================================================
def phase_a_set_report_interrupt(dev):
    phase_banner("A", "SET_REPORT → INTERRUPT ENDPOINT READ")
    log('INFO', 'El chip acepta SET_REPORT. ¿Responde por interrupt endpoint?')
    log('INFO', 'Técnica: Enviar comando USB → leer hidraw inmediatamente')
    
    # Open hidraw for reading
    try:
        fd_mouse = os.open(HIDRAW_MOUSE, os.O_RDONLY | os.O_NONBLOCK)
        fd_kbd = os.open(HIDRAW_KBD, os.O_RDONLY | os.O_NONBLOCK)
        log('OK', 'hidraw0 y hidraw2 abiertos para lectura')
    except PermissionError:
        log('FAIL', 'Sin permisos en hidraw. Ejecuta: sudo chmod 444 /dev/hidraw0 /dev/hidraw2')
        return
    
    # Flush pending data
    for fd in [fd_mouse, fd_kbd]:
        try:
            while True:
                p = select.poll()
                p.register(fd, select.POLLIN)
                ev = p.poll(50)
                if not ev:
                    break
                os.read(fd, 64)
                p.unregister(fd)
        except:
            pass
    
    def read_interrupt(timeout_ms=200):
        """Lee de ambos hidraw después de enviar un comando"""
        responses = []
        for fd, name in [(fd_mouse, 'mouse'), (fd_kbd, 'keyboard')]:
            try:
                p = select.poll()
                p.register(fd, select.POLLIN)
                events = p.poll(timeout_ms)
                if events:
                    data = os.read(fd, 64)
                    if data and len(data) > 0:
                        responses.append((name, bytes(data)))
                p.unregister(fd)
            except:
                pass
        return responses
    
    # Commands to try via SET_REPORT Feature 0xBA
    commands = [
        ([0xBA, 0x01] + [0]*30, "GET_VERSION"),
        ([0xBA, 0x02] + [0]*30, "GET_STATUS"),
        ([0xBA, 0x03] + [0]*30, "GET_CONFIG"),
        ([0xBA, 0x04] + [0]*30, "PAIR_MODE"),
        ([0xBA, 0x05] + [0]*30, "GET_ADDRESS"),
        ([0xBA, 0x06] + [0]*30, "GET_CHANNEL"),
        ([0xBA, 0x10] + [0]*30, "GET_FW_INFO"),
        ([0xBA, 0x55, 0xAA] + [0]*29, "MAGIC_55AA"),
        ([0xBA, 0xAA, 0x55] + [0]*29, "MAGIC_AA55"),
        ([0xBA, 0xFF] + [0]*30, "PING"),
        ([0xBA, 0x00, 0x01] + [0]*29, "READ_MEM_0"),
        ([0xBA, 0x00, 0x02] + [0]*29, "READ_MEM_1"),
        # Serial-derived commands (serial = b120300001)
        ([0xBA, 0xB1, 0x20, 0x30, 0x00, 0x01] + [0]*26, "SERIAL_ADDR"),
        ([0xBA, 0x12, 0x03, 0x00, 0x00, 0x01] + [0]*26, "SERIAL_DECODE"),
    ]
    
    total_responses = 0
    
    for cmd_data, cmd_name in commands:
        payload = bytes(cmd_data)
        
        # Try SET_REPORT Feature
        try:
            dev.ctrl_transfer(0x21, 0x09, (0x03 << 8) | 0xBA, 1, payload)
            time.sleep(0.05)
            
            responses = read_interrupt(150)
            if responses:
                for ep_name, resp_data in responses:
                    total_responses += 1
                    log('FIRE', f'{cmd_name} → INTERRUPT RESPONSE on {ep_name}!', resp_data)
            else:
                log('OK', f'{cmd_name} — sent (no interrupt response)')
        except usb.core.USBError as e:
            log('FAIL', f'{cmd_name}: {e}')
    
    # Report ID 0x04 commands
    print()
    log('PROBE', 'Probando Report ID 0x04 (Vendor Page 0xFFBC)...')
    
    for byte_val in range(16):
        payload = bytes([0x04, byte_val] + [0]*6)
        try:
            dev.ctrl_transfer(0x21, 0x09, (0x03 << 8) | 0x04, 1, payload)
            time.sleep(0.03)
            responses = read_interrupt(100)
            if responses:
                for ep_name, resp_data in responses:
                    total_responses += 1
                    log('FIRE', f'PAGE_0x04 cmd=0x{byte_val:02x} → RESPONSE on {ep_name}!', resp_data)
        except:
            pass
    
    log('INFO', f'Total interrupt responses: {total_responses}')
    
    os.close(fd_mouse)
    os.close(fd_kbd)

# ================================================================
# FASE B: Direct INTERRUPT endpoint read via pyusb
# ================================================================
def phase_b_direct_interrupt(dev):
    phase_banner("B", "DIRECT INTERRUPT ENDPOINT ACCESS")
    log('INFO', 'Leyendo directamente de los interrupt endpoints via pyusb')
    
    # Try to read from interrupt endpoints
    endpoints = [
        (0x81, 0, "EP 0x81 (keyboard)"),
        (0x82, 1, "EP 0x82 (mouse)"),
    ]
    
    for ep_addr, iface, desc in endpoints:
        # Send a command first
        try:
            payload = bytes([0xBA, 0x01] + [0]*30)
            dev.ctrl_transfer(0x21, 0x09, (0x03 << 8) | 0xBA, 1, payload)
        except:
            pass
        
        time.sleep(0.05)
        
        # Try to read from interrupt endpoint
        try:
            data = dev.read(ep_addr, 64, timeout=300)
            if data is not None and len(data) > 0:
                log('FIRE', f'{desc} — GOT DATA!', bytes(data))
            else:
                log('OK', f'{desc} — empty')
        except usb.core.USBTimeoutError:
            log('OK', f'{desc} — timeout (no data pending)')
        except usb.core.USBError as e:
            log('WARN', f'{desc} — {e}')

# ================================================================
# FASE C: Serial Number Analysis
# ================================================================
def phase_c_serial_analysis(dev):
    phase_banner("C", "SERIAL NUMBER FORENSICS")
    
    serial = "b120300001"
    log('INFO', f'Serial Number: "{serial}"')
    log('INFO', 'Analizando posibles significados...')
    
    # Decode attempts
    log('PROBE', 'Decodificando serial...')
    
    # As hex bytes
    log('INFO', f'  Como hex raw: {" ".join(f"0x{ord(c):02x}" for c in serial)}')
    
    # Possible structure: b + version + serial
    log('INFO', f'  Prefijo: "b" (posible batch/board)')
    log('INFO', f'  Versión: "1203" (posible v12.03 o fecha 2012-03)')
    log('INFO', f'  Número: "00001" (unidad #1)')
    
    # As possible RF address (5 bytes)
    # Convert serial digits to bytes
    try:
        addr_bytes = bytes([int(serial[i:i+2], 16) for i in range(0, 10, 2)])
        log('INFO', f'  Como dirección RF (hex pairs): {" ".join(f"{b:02x}" for b in addr_bytes)}')
    except:
        pass
    
    # Try numeric interpretation
    try:
        num_val = int(serial[1:])  # skip 'b' prefix
        log('INFO', f'  Como número: {num_val}')
        log('INFO', f'  En hex: 0x{num_val:08X}')
        # Split into possible channel + address
        log('INFO', f'  Posible canal RF: {num_val & 0x7F} (= {(num_val & 0x7F) + 2400} MHz)')
        log('INFO', f'  Posible dirección: 0x{(num_val >> 7):06X}')
    except:
        pass

# ================================================================
# FASE D: HID Output Report — LED/Command injection
# ================================================================
def phase_d_output_reports(dev):
    phase_banner("D", "HID OUTPUT REPORT INJECTION")
    log('INFO', 'Interface 0 tiene Output Report (LEDs del teclado)')
    log('INFO', 'Intentando inyectar datos por Output Report...')
    
    # The keyboard interface has an output report for LEDs
    # Byte format: bit0=NumLock, bit1=CapsLock, bit2=ScrollLock, bit3=Compose, bit4=Kana
    led_patterns = [
        (0x00, "All LEDs off"),
        (0x01, "NumLock ON"),
        (0x02, "CapsLock ON"),
        (0x04, "ScrollLock ON"),
        (0x07, "All LEDs ON"),
        (0x1F, "All bits ON"),
        (0xFF, "Full byte ON"),
    ]
    
    for led_val, desc in led_patterns:
        try:
            # SET_REPORT Output, Report ID 0, Interface 0
            dev.ctrl_transfer(0x21, 0x09, (0x02 << 8) | 0x00, 0, bytes([led_val]))
            log('OK', f'Output Report iface=0: {desc} (0x{led_val:02x}) — ACCEPTED')
        except usb.core.USBError as e:
            log('FAIL', f'Output Report iface=0: {desc} — {e}')
    
    # Try sending output reports to interface 1 (mouse)
    print()
    log('PROBE', 'Intentando Output Reports en interface 1 (mouse vendor)...')
    
    # Try various report IDs for output
    for report_id in [0x00, 0x01, 0x02, 0x03, 0x04, 0xBA]:
        try:
            payload = bytes([report_id, 0x01, 0x02, 0x03])
            dev.ctrl_transfer(0x21, 0x09, (0x02 << 8) | report_id, 1, payload)
            log('FOUND', f'Output Report 0x{report_id:02X} iface=1 — ACCEPTED!')
        except usb.core.USBError:
            pass

# ================================================================
# FASE E: Physical Descriptor dump
# ================================================================
def phase_e_physical_descriptor(dev):
    phase_banner("E", "PHYSICAL DESCRIPTOR EXTRACTION")
    log('PROBE', 'Extrayendo Physical Descriptors de ambas interfaces...')
    
    for iface in [0, 1]:
        for idx in range(5):
            try:
                result = dev.ctrl_transfer(
                    0x81,   # Standard, Interface-to-Host
                    0x06,   # GET_DESCRIPTOR
                    (0x23 << 8) | idx,  # Physical Descriptor, index
                    iface,
                    256
                )
                if result is not None and len(result) > 0:
                    log('FOUND', f'Physical Descriptor iface={iface} idx={idx}', bytes(result))
            except:
                pass

# ================================================================
# MAIN
# ================================================================
def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  🔥 YICHIP DONGLE CRACKER v2.0 — INTERRUPT ATTACK          ║")
    print("║  Serial: b120300001 | Vendor channel: WRITABLE             ║")
    print("║  Nobody has done this before. WE ARE FIRST.                ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        print("  ❌ Dongle no encontrado!")
        sys.exit(1)
    
    log('OK', f'Dongle: {dev.manufacturer} {dev.product} (serial: b120300001)')
    
    # Detach kernel drivers
    for iface in [0, 1]:
        try:
            if dev.is_kernel_driver_active(iface):
                dev.detach_kernel_driver(iface)
                log('OK', f'Kernel driver detached iface={iface}')
        except:
            pass
    
    try:
        dev.set_configuration()
    except:
        pass
    
    try:
        phase_a_set_report_interrupt(dev)
        phase_b_direct_interrupt(dev)
        phase_c_serial_analysis(dev)
        phase_d_output_reports(dev)
        phase_e_physical_descriptor(dev)
    except Exception as e:
        log('FAIL', f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        for iface in [0, 1]:
            try:
                usb.util.release_interface(dev, iface)
                dev.attach_kernel_driver(iface)
            except:
                pass
    
    # Summary
    print(f"\n{'═' * 65}")
    print(f"  📊 RESUMEN v2.0")
    print(f"{'═' * 65}")
    
    fire_items = [r for r in RESULTS if r['level'] in ('FOUND', 'FIRE')]
    print(f"  🔥 Descubrimientos: {len(fire_items)}")
    print(f"  📋 Total operaciones: {len(RESULTS)}")
    
    if fire_items:
        print(f"\n  🔥 HALLAZGOS:")
        for item in fire_items:
            print(f"    → {item['message']}")
            if item.get('data'):
                print(f"      {str(item['data'])[:80]}")
    
    # Save
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cracker_v2_results.json')
    with open(output, 'w') as f:
        json.dump({
            'tool': 'YICHIP Dongle Cracker v2.0',
            'timestamp': datetime.now().isoformat(),
            'serial': 'b120300001',
            'findings': len(fire_items),
            'results': RESULTS
        }, f, indent=2)
    
    print(f"\n  💾 {output}")
    print(f"\n  🏁 CRACKING v2.0 COMPLETADO!")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  YICHIP DONGLE CRACKER v1.0                                     ║
║  First-ever open source YICHIP USB dongle analysis toolkit       ║
║  Vendor: 3151 | Product: 3000 | Chip: YC1021 (probable)         ║
║                                                                  ║
║  Nobody has done this before. We are the first.                  ║
╚══════════════════════════════════════════════════════════════════╝

Techniques used:
1. USB Control Transfer probing (vendor/class/standard requests)
2. DFU bootloader discovery
3. HID Feature Report extraction
4. HID Output Report injection
5. USB String Descriptor enumeration
6. USB BOS Descriptor check
7. Vendor HID channel deep fuzzing (Report ID 0xBA)
8. USB reset & re-enumeration
"""

import usb.core
import usb.util
import struct
import time
import json
import os
import sys
from datetime import datetime

VENDOR_ID = 0x3151
PRODUCT_ID = 0x3000
RESULTS = []

def log(level, msg, data=None):
    """Log with formatting"""
    icons = {'INFO': '📋', 'OK': '✅', 'FAIL': '❌', 'WARN': '⚠️', 'FOUND': '🔴', 'PROBE': '🔍'}
    icon = icons.get(level, '  ')
    print(f"  {icon} {msg}")
    if data:
        if isinstance(data, (bytes, bytearray)):
            hex_str = ' '.join(f'{b:02x}' for b in data)
            print(f"     → [{len(data)} bytes] {hex_str}")
        else:
            print(f"     → {data}")
    
    RESULTS.append({
        'level': level,
        'message': msg,
        'data': data.hex() if isinstance(data, (bytes, bytearray)) else str(data) if data else None,
        'timestamp': datetime.now().isoformat()
    })

def phase_banner(num, title):
    print()
    print(f"{'═' * 65}")
    print(f"  FASE {num}: {title}")
    print(f"{'═' * 65}")

# ================================================================
# FASE 1: USB Device Deep Enumeration
# ================================================================
def phase1_enumeration(dev):
    phase_banner(1, "USB DEEP ENUMERATION")
    
    log('INFO', f'Device: {dev.manufacturer} {dev.product}')
    log('INFO', f'VID:PID = {dev.idVendor:#06x}:{dev.idProduct:#06x}')
    log('INFO', f'USB Version: {dev.bcdUSB:#06x}')
    log('INFO', f'Device Version: {dev.bcdDevice:#06x}')
    log('INFO', f'Device Class: {dev.bDeviceClass}')
    log('INFO', f'Max Packet Size: {dev.bMaxPacketSize0}')
    log('INFO', f'Num Configurations: {dev.bNumConfigurations}')
    
    # Try to read ALL string descriptors (0-255)
    print()
    log('PROBE', 'Buscando String Descriptors ocultos (0-255)...')
    found_strings = 0
    for i in range(256):
        try:
            s = usb.util.get_string(dev, i)
            if s and len(s.strip()) > 0:
                found_strings += 1
                log('FOUND', f'String Descriptor [{i}]: "{s}"')
        except:
            pass
    
    if found_strings == 0:
        log('WARN', 'No se encontraron strings adicionales')
    
    # Try BOS descriptor (USB 2.1+)
    print()
    log('PROBE', 'Intentando BOS Descriptor (Binary Object Store)...')
    try:
        bos = dev.ctrl_transfer(0x80, 0x06, 0x0F00, 0, 64)
        log('FOUND', 'BOS Descriptor encontrado!', bytes(bos))
    except:
        log('INFO', 'No BOS Descriptor (esperado para USB 2.0)')
    
    # Try to read device qualifier
    log('PROBE', 'Intentando Device Qualifier Descriptor...')
    try:
        qual = dev.ctrl_transfer(0x80, 0x06, 0x0600, 0, 10)
        log('FOUND', 'Device Qualifier encontrado!', bytes(qual))
    except:
        log('INFO', 'No Device Qualifier')

# ================================================================
# FASE 2: USB Control Transfer Fuzzing
# ================================================================
def phase2_control_fuzzing(dev):
    phase_banner(2, "USB CONTROL TRANSFER FUZZING")
    
    # Standard requests
    standard_requests = [
        (0x80, 0x00, 0, 0, 2, "GET_STATUS (Device)"),
        (0x81, 0x00, 0, 0, 2, "GET_STATUS (Interface 0)"),
        (0x81, 0x00, 0, 1, 2, "GET_STATUS (Interface 1)"),
        (0x82, 0x00, 0, 0x81, 2, "GET_STATUS (Endpoint 0x81)"),
        (0x82, 0x00, 0, 0x82, 2, "GET_STATUS (Endpoint 0x82)"),
    ]
    
    log('PROBE', 'Standard USB Requests...')
    for bmReq, bReq, wVal, wIdx, wLen, desc in standard_requests:
        try:
            result = dev.ctrl_transfer(bmReq, bReq, wVal, wIdx, wLen)
            log('OK', f'{desc}', bytes(result))
        except Exception as e:
            log('FAIL', f'{desc}: {e}')
    
    # Vendor-specific requests (the real hacking starts here)
    print()
    log('PROBE', 'Vendor-Specific USB Requests (bRequestType=0xC0)...')
    log('INFO', 'Esto es lo que NADIE ha probado con YICHIP...')
    
    vendor_hits = 0
    for bRequest in range(0x20):
        for wValue in [0x0000, 0x0001, 0x0100, 0x0200, 0xFF00]:
            try:
                result = dev.ctrl_transfer(
                    0xC0,       # Vendor, Device-to-Host
                    bRequest,   # Request
                    wValue,     # Value
                    0,          # Index
                    64          # Length
                )
                if result is not None and len(result) > 0:
                    vendor_hits += 1
                    log('FOUND', f'VENDOR REQUEST bReq=0x{bRequest:02x} wVal=0x{wValue:04x} RESPONDED!', bytes(result))
            except usb.core.USBError:
                pass
    
    if vendor_hits == 0:
        log('WARN', 'No vendor requests respondieron (chip muy cerrado)')
    
    # Class-specific requests (HID class)
    print()
    log('PROBE', 'HID Class Requests...')
    
    # GET_REPORT for each interface
    for iface in [0, 1]:
        for report_type in [1, 2, 3]:  # Input, Output, Feature
            type_name = {1: 'Input', 2: 'Output', 3: 'Feature'}[report_type]
            for report_id in [0, 1, 2, 3, 4, 0xBA]:
                try:
                    result = dev.ctrl_transfer(
                        0xA1,                           # Class, Interface-to-Host
                        0x01,                           # GET_REPORT
                        (report_type << 8) | report_id, # Type + ID
                        iface,                          # Interface
                        64                              # Length
                    )
                    if result is not None and len(result) > 0:
                        is_zero = all(b == 0 for b in result)
                        if not is_zero:
                            log('FOUND', f'GET_REPORT iface={iface} type={type_name} id=0x{report_id:02x} — DATA!', bytes(result))
                        else:
                            log('OK', f'GET_REPORT iface={iface} type={type_name} id=0x{report_id:02x} — zeros ({len(result)}b)')
                except usb.core.USBError:
                    pass
    
    # GET_IDLE and GET_PROTOCOL
    print()
    for iface in [0, 1]:
        try:
            result = dev.ctrl_transfer(0xA1, 0x02, 0, iface, 1)  # GET_IDLE
            log('OK', f'GET_IDLE iface={iface}', bytes(result))
        except:
            pass
        try:
            result = dev.ctrl_transfer(0xA1, 0x03, 0, iface, 1)  # GET_PROTOCOL
            log('OK', f'GET_PROTOCOL iface={iface}', bytes(result))
        except:
            pass

# ================================================================
# FASE 3: DFU / Bootloader Discovery
# ================================================================
def phase3_dfu_discovery(dev):
    phase_banner(3, "DFU / BOOTLOADER DISCOVERY")
    
    log('PROBE', 'Buscando DFU Runtime Descriptor...')
    try:
        # DFU functional descriptor
        result = dev.ctrl_transfer(0x80, 0x06, 0x2100, 0, 9)
        log('FOUND', 'DFU Descriptor encontrado!', bytes(result))
    except:
        log('INFO', 'No DFU runtime descriptor')
    
    log('PROBE', 'Intentando DFU DETACH (entrar en bootloader)...')
    try:
        # DFU_DETACH
        dev.ctrl_transfer(0x21, 0x00, 1000, 0, None)  # timeout 1000ms
        log('FOUND', 'DFU DETACH aceptado! El dispositivo podría estar en bootloader mode!')
    except usb.core.USBError as e:
        log('INFO', f'DFU DETACH rechazado: {e}')
    
    log('PROBE', 'Intentando DFU GET_STATUS...')
    try:
        result = dev.ctrl_transfer(0xA1, 0x03, 0, 0, 6)
        log('FOUND', 'DFU GET_STATUS respondió!', bytes(result))
    except:
        log('INFO', 'No DFU GET_STATUS')
    
    # Try common bootloader magic sequences
    print()
    log('PROBE', 'Probando secuencias de bootloader comunes...')
    
    bootloader_sequences = [
        (0x40, 0x00, 0x7777, 0, "Magic reboot 0x7777"),
        (0x40, 0x00, 0xDEAD, 0, "Magic reboot 0xDEAD"),
        (0x40, 0xFF, 0x0000, 0, "Vendor reset 0xFF"),
        (0x40, 0xFE, 0x0000, 0, "Vendor bootloader 0xFE"),
        (0x40, 0x01, 0xAAAA, 0, "ISP mode 0xAAAA"),
        (0x40, 0xB0, 0x0000, 0, "Boot mode 0xB0"),
        (0x40, 0xA5, 0x5A00, 0, "Unlock 0xA5/5A"),
        (0x21, 0x09, 0x0300, 0, "SET_REPORT Feature ID=0"),
    ]
    
    for bmReq, bReq, wVal, wIdx, desc in bootloader_sequences:
        try:
            dev.ctrl_transfer(bmReq, bReq, wVal, wIdx, None)
            log('FOUND', f'{desc} — ACCEPTED!')
        except usb.core.USBError as e:
            if 'Pipe' in str(e) or 'STALL' in str(e).upper():
                log('FAIL', f'{desc} — STALL')
            else:
                log('WARN', f'{desc} — {e}')

# ================================================================
# FASE 4: HID Feature Report Deep Scan
# ================================================================
def phase4_feature_reports(dev):
    phase_banner(4, "HID FEATURE REPORT DEEP SCAN")
    
    log('PROBE', 'Escaneando TODOS los Feature Reports (ID 0x00-0xFF) en interface 1...')
    
    found_features = 0
    for report_id in range(256):
        try:
            result = dev.ctrl_transfer(
                0xA1,                    # Class, Interface-to-Host
                0x01,                    # GET_REPORT
                (0x03 << 8) | report_id, # Feature Report
                1,                       # Interface 1 (mouse)
                64
            )
            if result is not None and len(result) > 0:
                is_zero = all(b == 0 for b in result)
                if not is_zero:
                    found_features += 1
                    log('FOUND', f'Feature Report 0x{report_id:02X} — NON-ZERO DATA!', bytes(result))
                elif report_id in [0, 1, 2, 3, 4, 0xBA]:
                    log('OK', f'Feature Report 0x{report_id:02X} — zeros ({len(result)}b)')
        except:
            pass
    
    log('INFO', f'Total Feature Reports con datos: {found_features}')
    
    # Also scan interface 0 (keyboard)
    print()
    log('PROBE', 'Escaneando Feature Reports en interface 0 (keyboard)...')
    for report_id in range(256):
        try:
            result = dev.ctrl_transfer(0xA1, 0x01, (0x03 << 8) | report_id, 0, 64)
            if result is not None and len(result) > 0 and not all(b == 0 for b in result):
                log('FOUND', f'Keyboard Feature Report 0x{report_id:02X}!', bytes(result))
        except:
            pass

# ================================================================
# FASE 5: SET_REPORT injection attempts
# ================================================================
def phase5_set_report(dev):
    phase_banner(5, "SET_REPORT INJECTION")
    
    log('PROBE', 'Intentando SET_REPORT en canal vendor (0xBA)...')
    
    # Try SET_REPORT with various payloads on the vendor channel
    payloads = [
        (0xBA, bytes([0xBA, 0x01] + [0]*30), "GET_VERSION via SET_REPORT"),
        (0xBA, bytes([0xBA, 0x55, 0xAA] + [0]*29), "Magic 55AA via SET_REPORT"),
        (0xBA, bytes([0xBA, 0xAA, 0x55, 0x01, 0x00] + [0]*27), "Config read via SET_REPORT"),
        (0xBA, bytes([0xBA, 0xFF, 0xFF, 0xFF] + [0]*28), "Broadcast via SET_REPORT"),
        (0x04, bytes([0x04, 0x01] + [0]*6), "Vendor Page 0xFFBC cmd 01"),
        (0x04, bytes([0x04, 0x55, 0xAA] + [0]*5), "Vendor Page 0xFFBC magic"),
    ]
    
    for report_id, payload, desc in payloads:
        # SET_REPORT (Output)
        try:
            dev.ctrl_transfer(
                0x21,                        # Class, Host-to-Interface
                0x09,                        # SET_REPORT
                (0x02 << 8) | report_id,     # Output Report
                1,                           # Interface 1
                payload
            )
            log('OK', f'SET_REPORT Output 0x{report_id:02X}: {desc} — ACCEPTED')
            
            # Try to read response
            time.sleep(0.1)
            try:
                result = dev.ctrl_transfer(0xA1, 0x01, (0x01 << 8) | report_id, 1, 64)
                if result is not None and len(result) > 0 and not all(b == 0 for b in result):
                    log('FOUND', f'RESPONSE to {desc}!', bytes(result))
            except:
                pass
        except usb.core.USBError as e:
            log('FAIL', f'SET_REPORT Output 0x{report_id:02X}: {desc} — {e}')
        
        # SET_REPORT (Feature)
        try:
            dev.ctrl_transfer(
                0x21,
                0x09,
                (0x03 << 8) | report_id,    # Feature Report
                1,
                payload
            )
            log('OK', f'SET_REPORT Feature 0x{report_id:02X}: {desc} — ACCEPTED')
            
            time.sleep(0.1)
            try:
                result = dev.ctrl_transfer(0xA1, 0x01, (0x03 << 8) | report_id, 1, 64)
                if result is not None and len(result) > 0 and not all(b == 0 for b in result):
                    log('FOUND', f'FEATURE RESPONSE to {desc}!', bytes(result))
            except:
                pass
        except usb.core.USBError as e:
            log('FAIL', f'SET_REPORT Feature 0x{report_id:02X}: {desc} — {e}')

# ================================================================
# FASE 6: Brute Force vendor channel protocol
# ================================================================
def phase6_bruteforce(dev):
    phase_banner(6, "VENDOR CHANNEL BRUTE FORCE (Report 0xBA)")
    
    log('PROBE', 'SET_REPORT + GET_REPORT con headers de 2 bytes (0x00-0x10 x 0x00-0x10)...')
    log('INFO', 'Probando 289 combinaciones...')
    
    hits = 0
    for b1 in range(0x11):
        for b2 in range(0x11):
            payload = bytes([0xBA, b1, b2] + [0]*29)
            try:
                # Send
                dev.ctrl_transfer(0x21, 0x09, (0x03 << 8) | 0xBA, 1, payload)
                time.sleep(0.02)
                
                # Read
                try:
                    result = dev.ctrl_transfer(0xA1, 0x01, (0x03 << 8) | 0xBA, 1, 32)
                    if result is not None and len(result) > 0 and not all(b == 0 for b in result):
                        hits += 1
                        log('FOUND', f'CMD [{b1:02x} {b2:02x}] RESPONDED!', bytes(result))
                except:
                    pass
            except:
                pass
    
    log('INFO', f'Brute force completado: {hits} respuestas encontradas')
    
    # Try with SET_REPORT Output type too
    print()
    log('PROBE', 'Repitiendo con Output Reports...')
    
    for b1 in [0x00, 0x01, 0x55, 0xAA, 0xFF]:
        for b2 in range(0x11):
            payload = bytes([0xBA, b1, b2] + [0]*29)
            try:
                dev.ctrl_transfer(0x21, 0x09, (0x02 << 8) | 0xBA, 1, payload)
                time.sleep(0.02)
                try:
                    result = dev.ctrl_transfer(0xA1, 0x01, (0x01 << 8) | 0xBA, 1, 32)
                    if result is not None and len(result) > 0 and not all(b == 0 for b in result):
                        hits += 1
                        log('FOUND', f'OUTPUT CMD [{b1:02x} {b2:02x}] RESPONDED!', bytes(result))
                except:
                    pass
            except:
                pass
    
    log('INFO', f'Total hits: {hits}')

# ================================================================
# FASE 7: USB Configuration manipulation  
# ================================================================
def phase7_config(dev):
    phase_banner(7, "USB CONFIGURATION ANALYSIS")
    
    # Try to read additional configuration descriptors
    log('PROBE', 'Leyendo Configuration Descriptors adicionales...')
    for config_idx in range(3):
        try:
            result = dev.ctrl_transfer(0x80, 0x06, (0x02 << 8) | config_idx, 0, 255)
            log('FOUND', f'Config Descriptor [{config_idx}]', bytes(result))
        except:
            if config_idx == 0:
                log('FAIL', f'Config Descriptor [{config_idx}] no accesible')
    
    # Try to read HID descriptors directly
    print()
    log('PROBE', 'Leyendo HID Report Descriptors via control transfer...')
    for iface in [0, 1]:
        try:
            # GET_DESCRIPTOR for HID Report
            result = dev.ctrl_transfer(
                0x81,   # Standard, Interface-to-Host
                0x06,   # GET_DESCRIPTOR
                0x2200, # HID Report Descriptor
                iface,
                256
            )
            log('OK', f'HID Report Descriptor iface={iface} ({len(result)} bytes)', bytes(result))
        except Exception as e:
            log('FAIL', f'HID Report Descriptor iface={iface}: {e}')
    
    # Check for HID Physical Descriptor
    print()
    log('PROBE', 'Buscando HID Physical Descriptors...')
    for iface in [0, 1]:
        try:
            result = dev.ctrl_transfer(0x81, 0x06, 0x2300, iface, 64)
            log('FOUND', f'Physical Descriptor iface={iface}!', bytes(result))
        except:
            pass

# ================================================================
# MAIN
# ================================================================
def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  🔥 YICHIP DONGLE CRACKER v1.0                            ║")
    print("║  First-ever YICHIP USB analysis toolkit                    ║")
    print("║  github.com/??? — COMING SOON                             ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🎯 Target: YICHIP {VENDOR_ID:#06x}:{PRODUCT_ID:#06x}")
    print()
    
    # Find device
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        print("  ❌ Dongle YICHIP no encontrado!")
        print("  💡 ¿Está conectado el dongle?")
        sys.exit(1)
    
    log('OK', 'Dongle YICHIP encontrado!')
    
    # Detach kernel drivers
    for iface in [0, 1]:
        try:
            if dev.is_kernel_driver_active(iface):
                dev.detach_kernel_driver(iface)
                log('OK', f'Kernel driver detached de interface {iface}')
        except Exception as e:
            log('WARN', f'No se pudo detach interface {iface}: {e}')
    
    # Set configuration
    try:
        dev.set_configuration()
        log('OK', 'Configuración USB establecida')
    except:
        log('WARN', 'No se pudo establecer configuración (puede estar en uso)')
    
    # Run all phases
    try:
        phase1_enumeration(dev)
        phase2_control_fuzzing(dev)
        phase3_dfu_discovery(dev)
        phase4_feature_reports(dev)
        phase5_set_report(dev)
        phase6_bruteforce(dev)
        phase7_config(dev)
    except Exception as e:
        log('FAIL', f'Error durante análisis: {e}')
    finally:
        # Re-attach kernel drivers
        for iface in [0, 1]:
            try:
                usb.util.release_interface(dev, iface)
                dev.attach_kernel_driver(iface)
            except:
                pass
    
    # Summary
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  📊 RESUMEN FINAL                                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    found_items = [r for r in RESULTS if r['level'] == 'FOUND']
    ok_items = [r for r in RESULTS if r['level'] == 'OK']
    fail_items = [r for r in RESULTS if r['level'] == 'FAIL']
    
    print(f"  🔴 Descubrimientos:  {len(found_items)}")
    print(f"  ✅ Éxitos:           {len(ok_items)}")
    print(f"  ❌ Rechazados:       {len(fail_items)}")
    print(f"  📋 Total operaciones: {len(RESULTS)}")
    print()
    
    if found_items:
        print("  🔥 HALLAZGOS IMPORTANTES:")
        for item in found_items:
            print(f"    → {item['message']}")
            if item['data']:
                print(f"      Data: {item['data'][:80]}...")
        print()
    
    # Save results
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cracker_results.json')
    with open(output_path, 'w') as f:
        json.dump({
            'tool': 'YICHIP Dongle Cracker v1.0',
            'timestamp': datetime.now().isoformat(),
            'target': f'{VENDOR_ID:#06x}:{PRODUCT_ID:#06x}',
            'total_operations': len(RESULTS),
            'discoveries': len(found_items),
            'successes': len(ok_items),
            'failures': len(fail_items),
            'results': RESULTS,
            'discoveries_detail': [
                {'message': r['message'], 'data': r['data']} 
                for r in found_items
            ]
        }, f, indent=2)
    
    print(f"  💾 Resultados: {output_path}")
    print()
    print("  🏁 CRACKING COMPLETADO!")
    print()

if __name__ == '__main__':
    main()

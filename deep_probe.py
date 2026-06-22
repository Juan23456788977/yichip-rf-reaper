#!/usr/bin/env python3
"""
YICHIP DEEP PROBE - Autopsia completa del chip
================================================
Envía comandos vendor al canal oculto Report ID 0xBA
e intenta extraer toda la info posible del firmware.
"""

import os
import sys
import time
import struct
import select
import json

DEV = '/dev/hidraw2'

def hex_dump(data):
    return ' '.join(f'{b:02x}' for b in data)

def send_and_recv(fd, report_id, cmd_bytes, label, timeout=0.3):
    """Envía un comando y espera respuesta"""
    # Construir paquete: Report ID + data (total 32 bytes)
    packet = bytes([report_id]) + bytes(cmd_bytes) + bytes(31 - len(cmd_bytes))
    
    result = {
        'label': label,
        'sent': hex_dump(packet[:16]),
        'response': None,
        'status': 'NO_RESPONSE'
    }
    
    try:
        os.write(fd, packet)
        time.sleep(0.05)
        
        # Intentar leer respuesta
        poll = select.poll()
        poll.register(fd, select.POLLIN)
        events = poll.poll(int(timeout * 1000))
        
        if events:
            response = os.read(fd, 64)
            if response:
                result['response'] = hex_dump(response)
                result['raw'] = list(response)
                result['status'] = 'RESPONSE'
                # Check if it's all zeros
                if all(b == 0 for b in response):
                    result['status'] = 'ZERO_RESPONSE'
        
        poll.unregister(fd)
    except OSError as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)
    
    return result

def deep_probe():
    print("=" * 65)
    print("🔬 YICHIP DEEP PROBE — Autopsia del Chip")
    print("=" * 65)
    print(f"📍 Device: {DEV}")
    print()
    
    try:
        fd = os.open(DEV, os.O_RDWR | os.O_NONBLOCK)
    except PermissionError:
        print("❌ Sin permisos. Ejecuta: sudo chmod 666 /dev/hidraw2")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    print("✅ Dispositivo abierto en modo lectura/escritura")
    print()
    
    # Flush any pending data
    try:
        while True:
            poll = select.poll()
            poll.register(fd, select.POLLIN)
            events = poll.poll(100)
            if not events:
                break
            os.read(fd, 64)
            poll.unregister(fd)
    except:
        pass
    
    all_results = []
    
    # ============================================================
    # FASE 1: Comandos estándar de chips 2.4GHz
    # ============================================================
    print("📡 FASE 1: Comandos estándar de chips RF")
    print("-" * 50)
    
    standard_cmds = [
        ([0x01], "GET_VERSION — Leer versión firmware"),
        ([0x02], "GET_STATUS — Estado del receptor"),
        ([0x03], "GET_CONFIG — Configuración actual"),
        ([0x04], "PAIR_MODE — Intentar modo emparejamiento"),
        ([0x05], "GET_ADDRESS — Dirección RF del mouse"),
        ([0x06], "GET_CHANNEL — Canal RF actual"),
        ([0x07], "GET_POWER — Nivel de potencia RF"),
        ([0x08], "RESET — Soft reset"),
        ([0x0A], "GET_BATTERY — Nivel batería mouse"),
        ([0x0F], "GET_SERIAL — Número de serie"),
        ([0x10], "GET_FW_BUILD — Build del firmware"),
        ([0xFF], "PING — Echo test"),
    ]
    
    for cmd, label in standard_cmds:
        result = send_and_recv(fd, 0xBA, cmd, label)
        all_results.append(result)
        
        icon = "✅" if result['status'] == 'RESPONSE' else \
               "⚪" if result['status'] == 'ZERO_RESPONSE' else \
               "❌" if result['status'] == 'ERROR' else "⏳"
        
        print(f"  {icon} {label}")
        if result['response']:
            print(f"     → {result['response']}")
        print()
    
    # ============================================================
    # FASE 2: Comandos vendor YICHIP específicos
    # ============================================================
    print("⚡ FASE 2: Comandos YICHIP específicos")
    print("-" * 50)
    
    yichip_cmds = [
        ([0x55, 0xAA], "YICHIP_MAGIC_1 — Secuencia mágica 55 AA"),
        ([0xAA, 0x55], "YICHIP_MAGIC_2 — Secuencia mágica AA 55"),
        ([0x55, 0x55], "YICHIP_MAGIC_3 — Secuencia mágica 55 55"),
        ([0xA5, 0x5A], "YICHIP_UNLOCK — Intento desbloqueo"),
        ([0x5A, 0xA5], "YICHIP_UNLOCK_2 — Intento desbloqueo inverso"),
        ([0x00, 0x01], "YICHIP_ENTER_CONFIG — Modo configuración"),
        ([0x00, 0xFF], "YICHIP_FACTORY_RESET — Factory reset"),
        ([0x01, 0x00, 0x00, 0x01], "YICHIP_READ_REG_0 — Leer registro 0"),
        ([0x01, 0x00, 0x00, 0x02], "YICHIP_READ_REG_1 — Leer registro 1"),
        ([0x01, 0x00, 0x00, 0x03], "YICHIP_READ_REG_2 — Leer registro 2"),
        ([0x01, 0x00, 0x00, 0x04], "YICHIP_READ_REG_3 — Leer registro 3"),
    ]
    
    for cmd, label in yichip_cmds:
        result = send_and_recv(fd, 0xBA, cmd, label)
        all_results.append(result)
        
        icon = "✅" if result['status'] == 'RESPONSE' else \
               "⚪" if result['status'] == 'ZERO_RESPONSE' else \
               "❌" if result['status'] == 'ERROR' else "⏳"
        
        print(f"  {icon} {label}")
        if result['response']:
            print(f"     → {result['response']}")
        print()
    
    # ============================================================
    # FASE 3: Sonda Report ID 0x04 (Vendor Page 0xFFBC)
    # ============================================================
    print("🔮 FASE 3: Vendor Page 0xFFBC (Report ID 0x04)")
    print("-" * 50)
    
    page_cmds = [
        ([0x00], "PAGE_FFBC_READ_0"),
        ([0x01], "PAGE_FFBC_READ_1"),
        ([0xFF], "PAGE_FFBC_PING"),
    ]
    
    for cmd, label in page_cmds:
        result = send_and_recv(fd, 0x04, cmd, label)
        all_results.append(result)
        
        icon = "✅" if result['status'] == 'RESPONSE' else \
               "⚪" if result['status'] == 'ZERO_RESPONSE' else \
               "❌" if result['status'] == 'ERROR' else "⏳"
        
        print(f"  {icon} {label}")
        if result['response']:
            print(f"     → {result['response']}")
        print()
    
    # ============================================================
    # FASE 4: Brute force de los primeros bytes (0x00-0x20)
    # ============================================================
    print("💣 FASE 4: Brute Force — Escaneando comandos 0x00 a 0x30")
    print("-" * 50)
    
    interesting = []
    for i in range(0x00, 0x31):
        result = send_and_recv(fd, 0xBA, [i], f"CMD_0x{i:02X}", timeout=0.15)
        
        if result['status'] == 'RESPONSE' and result.get('raw'):
            # Check if non-trivial response
            raw = result['raw']
            if not all(b == 0 for b in raw) and not all(b == raw[0] for b in raw):
                interesting.append(result)
                print(f"  🔴 CMD 0x{i:02X} → {result['response']}")
        elif result['status'] == 'RESPONSE':
            interesting.append(result)
    
    if not interesting:
        print("  ⚪ Ningún comando devolvió datos interesantes")
    
    print()
    
    # ============================================================
    # RESUMEN
    # ============================================================
    responded = [r for r in all_results if r['status'] in ('RESPONSE', 'ZERO_RESPONSE')]
    non_zero = [r for r in all_results if r['status'] == 'RESPONSE' and r.get('raw') and not all(b == 0 for b in r['raw'])]
    
    print("=" * 65)
    print("📋 RESUMEN DE AUTOPSIA")
    print("=" * 65)
    print(f"  Total comandos enviados: {len(all_results) + 0x31}")
    print(f"  Respuestas recibidas:    {len(responded)}")
    print(f"  Respuestas con datos:    {len(non_zero)}")
    print(f"  Errores:                 {len([r for r in all_results if r['status'] == 'ERROR'])}")
    print()
    
    if non_zero:
        print("🔥 DATOS EXTRAÍDOS:")
        for r in non_zero:
            print(f"  [{r['label']}]")
            print(f"  → {r['response']}")
            print()
    
    # Guardar resultados
    output_path = os.path.join(os.path.dirname(__file__), 'probe_results.json')
    with open(output_path, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'device': DEV,
            'total_commands': len(all_results) + 0x31,
            'responses': len(responded),
            'interesting': len(non_zero),
            'results': all_results,
            'brute_force_hits': [{'cmd': f'0x{r["label"].split("_")[-1]}', 'response': r.get('response')} for r in interesting],
        }, f, indent=2, default=str)
    print(f"💾 Resultados guardados en: {output_path}")
    
    os.close(fd)
    print()
    print("🏁 Autopsia completada!")

if __name__ == '__main__':
    deep_probe()

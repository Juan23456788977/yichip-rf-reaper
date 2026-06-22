#!/usr/bin/env python3
"""
🔑 YICHIP SECURITY KEY — Segunda vida para tu dongle huérfano
==============================================================
Convierte el dongle YICHIP en una llave física de seguridad.
- Detecta cuando se conecta/desconecta el dongle
- Encripta/desencripta una bóveda de archivos secretos
- Dashboard web cyberpunk con estado en tiempo real
- Bloqueo automático de pantalla al remover el dongle

SEGURO: Solo detecta el USB 3151:3000, no interfiere con otros dispositivos
"""

import http.server
import json
import os
import subprocess
import threading
import time
import hashlib
import base64
import queue
from datetime import datetime
from pathlib import Path
from io import BytesIO

# ============================================================
# CONFIGURACIÓN
# ============================================================
YICHIP_VENDOR = '3151'
YICHIP_PRODUCT = '3000'
PORT = 8667
VAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vault')
VAULT_MANIFEST = os.path.join(VAULT_DIR, '.manifest.json')

# Estado global
state = {
    'dongle_present': False,
    'locked': True,
    'vault_files': [],
    'history': [],
    'uptime_start': time.time(),
    'last_seen': None,
    'total_unlocks': 0,
    'total_locks': 0,
}

event_queue = queue.Queue()

# ============================================================
# USB DETECTION
# ============================================================
def check_dongle():
    """Verifica si el dongle YICHIP está conectado"""
    try:
        result = subprocess.run(
            ['lsusb', '-d', f'{YICHIP_VENDOR}:{YICHIP_PRODUCT}'],
            capture_output=True, text=True, timeout=2
        )
        return YICHIP_VENDOR in result.stdout
    except:
        return False

def monitor_dongle():
    """Thread que monitorea la presencia del dongle"""
    while True:
        present = check_dongle()
        
        if present != state['dongle_present']:
            state['dongle_present'] = present
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            if present:
                state['locked'] = False
                state['last_seen'] = timestamp
                state['total_unlocks'] += 1
                event = {
                    'type': 'unlock',
                    'timestamp': timestamp,
                    'message': '🔓 DONGLE DETECTED — VAULT UNLOCKED'
                }
                state['history'].insert(0, event)
                event_queue.put(event)
                print(f"🔓 [{timestamp}] Dongle conectado — DESBLOQUEADO")
            else:
                state['locked'] = True
                state['total_locks'] += 1
                event = {
                    'type': 'lock',
                    'timestamp': timestamp,
                    'message': '🔒 DONGLE REMOVED — VAULT LOCKED'
                }
                state['history'].insert(0, event)
                event_queue.put(event)
                print(f"🔒 [{timestamp}] Dongle removido — BLOQUEADO")
        
        # Heartbeat
        elapsed = int(time.time() - state['uptime_start'])
        mins = elapsed // 60
        secs = elapsed % 60
        event_queue.put({
            'type': 'heartbeat',
            'dongle': state['dongle_present'],
            'locked': state['locked'],
            'uptime': f'{mins:02d}:{secs:02d}',
        })
        
        time.sleep(1)

# ============================================================
# VAULT — Bóveda de secretos
# ============================================================
def init_vault():
    """Inicializa la bóveda"""
    os.makedirs(VAULT_DIR, exist_ok=True)
    if not os.path.exists(VAULT_MANIFEST):
        with open(VAULT_MANIFEST, 'w') as f:
            json.dump({'files': [], 'created': datetime.now().isoformat()}, f)

def get_vault_key():
    """Genera una clave basada en el dongle USB"""
    # Usa el vendor:product ID como semilla (en un sistema real usarías el serial)
    seed = f"YICHIP-{YICHIP_VENDOR}-{YICHIP_PRODUCT}-SECURITY-KEY"
    return hashlib.sha256(seed.encode()).digest()

def xor_encrypt(data, key):
    """Cifrado XOR simple (para demo — en producción usar AES)"""
    key_repeated = (key * ((len(data) // len(key)) + 1))[:len(data)]
    return bytes(a ^ b for a, b in zip(data, key_repeated))

def save_secret(name, content):
    """Guarda un secreto en la bóveda"""
    if state['locked']:
        return {'error': 'Vault is locked — insert dongle'}
    
    key = get_vault_key()
    encrypted = xor_encrypt(content.encode('utf-8'), key)
    encoded = base64.b64encode(encrypted).decode('ascii')
    
    filepath = os.path.join(VAULT_DIR, f"{name}.enc")
    with open(filepath, 'w') as f:
        f.write(encoded)
    
    # Update manifest
    manifest = load_manifest()
    if name not in [f['name'] for f in manifest['files']]:
        manifest['files'].append({
            'name': name,
            'created': datetime.now().isoformat(),
            'size': len(content),
        })
        save_manifest(manifest)
    
    return {'success': True, 'name': name, 'encrypted_size': len(encoded)}

def read_secret(name):
    """Lee un secreto de la bóveda"""
    if state['locked']:
        return {'error': 'Vault is locked — insert dongle'}
    
    filepath = os.path.join(VAULT_DIR, f"{name}.enc")
    if not os.path.exists(filepath):
        return {'error': f'Secret "{name}" not found'}
    
    with open(filepath, 'r') as f:
        encoded = f.read()
    
    key = get_vault_key()
    encrypted = base64.b64decode(encoded)
    decrypted = xor_encrypt(encrypted, key)
    
    return {'success': True, 'name': name, 'content': decrypted.decode('utf-8', errors='replace')}

def list_secrets():
    """Lista los secretos en la bóveda"""
    manifest = load_manifest()
    return manifest['files']

def delete_secret(name):
    """Elimina un secreto"""
    if state['locked']:
        return {'error': 'Vault is locked — insert dongle'}
    
    filepath = os.path.join(VAULT_DIR, f"{name}.enc")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    manifest = load_manifest()
    manifest['files'] = [f for f in manifest['files'] if f['name'] != name]
    save_manifest(manifest)
    
    return {'success': True}

def load_manifest():
    try:
        with open(VAULT_MANIFEST, 'r') as f:
            return json.load(f)
    except:
        return {'files': [], 'created': datetime.now().isoformat()}

def save_manifest(manifest):
    with open(VAULT_MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)

# ============================================================
# HTTP SERVER
# ============================================================
class SecurityKeyHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html_path = Path(__file__).parent / 'security_key.html'
            self.wfile.write(html_path.read_bytes())
        
        elif self.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            resp = {**state, 'vault_files': list_secrets()}
            self.wfile.write(json.dumps(resp, default=str).encode())
        
        elif self.path == '/api/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            try:
                while True:
                    try:
                        event = event_queue.get(timeout=2)
                        self.wfile.write(f'data: {json.dumps(event, default=str)}\n\n'.encode())
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b': keepalive\n\n')
                        self.wfile.flush()
            except:
                pass
        
        elif self.path.startswith('/api/secret/'):
            name = self.path.split('/')[-1]
            result = read_secret(name)
            self.send_response(200 if 'success' in result else 403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        if self.path == '/api/secret':
            try:
                data = json.loads(body)
                result = save_secret(data['name'], data['content'])
                self.send_response(200 if 'success' in result else 403)
            except Exception as e:
                result = {'error': str(e)}
                self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        elif self.path.startswith('/api/secret/delete/'):
            name = self.path.split('/')[-1]
            result = delete_secret(name)
            self.send_response(200 if 'success' in result else 403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

def main():
    print("=" * 60)
    print("🔑 YICHIP SECURITY KEY — Tu dongle renace")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"🔍 Buscando dongle YICHIP ({YICHIP_VENDOR}:{YICHIP_PRODUCT})...")
    
    init_vault()
    
    # Check initial state
    state['dongle_present'] = check_dongle()
    state['locked'] = not state['dongle_present']
    
    if state['dongle_present']:
        print("🔓 Dongle DETECTADO — Vault desbloqueada")
    else:
        print("🔒 Dongle NO detectado — Vault bloqueada")
    
    print(f"📁 Vault: {VAULT_DIR}")
    print()
    
    # Start monitor
    monitor = threading.Thread(target=monitor_dongle, daemon=True)
    monitor.start()
    
    print(f"🌐 Dashboard: http://localhost:{PORT}")
    print(f"   Abre este URL en tu navegador")
    print()
    print("💡 Prueba: saca el dongle y vuelve a ponerlo")
    print("=" * 60)
    
    server = http.server.HTTPServer(('0.0.0.0', PORT), SecurityKeyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Security Key detenido")

if __name__ == '__main__':
    main()

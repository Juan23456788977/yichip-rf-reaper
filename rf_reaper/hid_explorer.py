import hid
import sys
import time

def list_device_interfaces(vid, pid):
    print(f"Buscando interfaces para VID: {hex(vid)}, PID: {hex(pid)}...")
    devices = hid.enumerate(vid, pid)
    
    if not devices:
        print("No se encontraron dispositivos con esos identificadores.")
        print("Asegúrate de que el dongle esté conectado y las reglas de udev estén aplicadas.")
        return []
    
    print("\nInterfaces encontradas:")
    for idx, dev in enumerate(devices):
        print(f"\n[{idx}] Dispositivo:")
        print(f"  Path: {dev['path'].decode('utf-8') if isinstance(dev['path'], bytes) else dev['path']}")
        print(f"  Interface Number: {dev['interface_number']}")
        print(f"  Manufacturer: {dev['manufacturer_string']}")
        print(f"  Product: {dev['product_string']}")
        print(f"  Usage Page: {hex(dev['usage_page']) if dev['usage_page'] is not None else 'None'} | Usage: {hex(dev['usage']) if dev['usage'] is not None else 'None'}")
    
    return devices

def monitor_interface(device_info):
    try:
        device = hid.device()
        device.open_path(device_info['path'])
        device.set_nonblocking(True)
        
        print(f"\nEscuchando datos en la interfaz {device_info['interface_number']}...")
        print("Mueve el periférico emparejado o presiona sus botones para ver los reportes.")
        print("Presiona Ctrl+C para salir.\n")
        
        while True:
            # Leer hasta 64 bytes de la interfaz
            data = device.read(64)
            if data:
                timestamp = time.strftime("%H:%M:%S")
                hex_data = " ".join([f"{b:02X}" for b in data])
                print(f"[{timestamp}] Report (Len={len(data)}): {hex_data}")
            time.sleep(0.01)  # Pequeña pausa para no saturar la CPU
            
    except IOError as e:
        print(f"Error de E/S al abrir o leer el dispositivo: {e}")
        print("Verifica los permisos de lectura/escritura sobre el archivo hidraw correspondiente.")
    except KeyboardInterrupt:
        print("\nMonitoreo finalizado por el usuario.")
    finally:
        try:
            device.close()
        except:
            pass

if __name__ == "__main__":
    VID = 0x3151
    PID = 0x3000
    
    interfaces = list_device_interfaces(VID, PID)
    
    if not interfaces:
        sys.exit(1)
        
    try:
        selection = input("\nSelecciona el índice del dispositivo/interfaz que deseas monitorear: ")
        idx = int(selection)
        if 0 <= idx < len(interfaces):
            monitor_interface(interfaces[idx])
        else:
            print("Selección inválida.")
    except ValueError:
        print("Entrada no válida. Por favor, introduce un número entero.")

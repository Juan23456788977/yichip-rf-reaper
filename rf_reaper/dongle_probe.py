#!/usr/bin/env python3
"""Decode YICHIP dongle HID report descriptors"""
import os

def read_descriptor(path):
    with open(path, 'rb') as f:
        return f.read()

usage_pages = {
    0x01: "Generic Desktop", 0x07: "Keyboard/Keypad", 0x08: "LED",
    0x09: "Button", 0x0C: "Consumer"
}

desktop_usages = {
    0x01: "Pointer", 0x02: "Mouse", 0x06: "Keyboard", 0x30: "X",
    0x31: "Y", 0x38: "Wheel", 0x80: "System Control"
}

# Interface 0: Keyboard
print("=" * 60)
print("KEYBOARD HID Report Descriptor")
print("=" * 60)

kb_path = "/sys/bus/usb/devices/2-1.2/2-1.2:1.0/0003:3151:3000.0002/report_descriptor"
kb_desc = read_descriptor(kb_path)
print(f"  Size: {len(kb_desc)} bytes")
print(f"  Hex:  {' '.join(f'{b:02x}' for b in kb_desc)}")

# Interface 1: Mouse/Consumer
print()
print("=" * 60)
print("MOUSE/SYSTEM/CONSUMER HID Report Descriptor")
print("=" * 60)

mouse_path = "/sys/bus/usb/devices/2-1.2/2-1.2:1.1/0003:3151:3000.0004/report_descriptor"
mouse_desc = read_descriptor(mouse_path)
print(f"  Size: {len(mouse_desc)} bytes")
print(f"  Hex:  {' '.join(f'{b:02x}' for b in mouse_desc)}")

# Count report IDs
report_ids = set()
i = 0
while i < len(mouse_desc):
    prefix = mouse_desc[i]
    bSize = prefix & 0x03
    if bSize == 3: bSize = 4
    bType = (prefix >> 2) & 0x03
    bTag = (prefix >> 4) & 0x0F
    
    if bType == 1 and bTag == 0x08:  # Report ID
        if bSize >= 1 and i + 1 < len(mouse_desc):
            report_ids.add(mouse_desc[i + 1])
    i += 1 + bSize

print(f"  Report IDs: {sorted(report_ids)}")

print()
print("=" * 60)
print("CAPABILITIES SUMMARY")
print("=" * 60)
print()
print("  Interface 0 (Keyboard):")
print("    - Full keyboard (Boot protocol)")
print("    - 8 modifier keys (Ctrl, Shift, Alt, GUI)")
print("    - 6-key rollover")
print("    - 5 LEDs")
print()
print("  Interface 1 (Composite):")
print(f"    - Report IDs: {sorted(report_ids)}")
if 1 in report_ids: print("    - Report 1: Mouse (5 buttons + XY + wheel)")
if 2 in report_ids: print("    - Report 2: Keyboard (consumer/multimedia)")  
if 3 in report_ids: print("    - Report 3: System Control (power/sleep/wake)")
if 4 in report_ids: print("    - Report 4: Consumer Control (volume/media)")
if 5 in report_ids: print("    - Report 5: Extra features")
print()
print("  THE DONGLE IS A FULL HID COMBO RECEIVER")
print("  It accepts keyboard + mouse + media + system HID events")
print("  from the paired 2.4GHz wireless device (mouse que dejaste en Espana)")
print()
print("  WHAT WE CAN DO WITH IT:")
print("  1. READ incoming HID reports (if device paired & transmitting)")
print("  2. DETECT pairing state via URB monitoring")
print("  3. USE as BadUSB — the dongle IS registered as keyboard/mouse")
print("     The OS already sees it as a keyboard input device!")
print("  4. MONITOR for wireless reconnections")

#!/usr/bin/env python3
"""midi_diag.py — lista todas as portas MIDI e imprime TUDO que chega de cada uma."""
import time
import rtmidi

probe = rtmidi.MidiIn()
names = probe.get_ports()
print("Portas de entrada encontradas:")
for i, n in enumerate(names):
    print(f"  [{i}] {n}")
if not names:
    raise SystemExit("Nenhuma porta MIDI de entrada.")

ins = []
for i, n in enumerate(names):
    m = rtmidi.MidiIn()
    m.ignore_types(sysex=False, timing=True, active_sense=True)

    def cb(event, data, name=n):
        msg, _ = event
        hexs = " ".join(f"{b:02X}" for b in msg)
        kind = msg[0] & 0xF0
        label = {0x80: "note_off", 0x90: "note_on", 0xB0: "CC",
                 0xC0: "program", 0xE0: "pitch", 0xF0: "sysex/sys"}.get(kind, "?")
        extra = ""
        if kind == 0xB0 and len(msg) >= 3:
            extra = f"  -> CC {msg[1]} valor {msg[2]} canal {(msg[0] & 0x0F) + 1}"
        print(f"[{name}] {label:9s} {hexs}{extra}", flush=True)

    m.set_callback(cb)
    m.open_port(i)
    ins.append(m)

print("\nGire os knobs, aperte botões e pads (Ctrl+C para sair)...\n")
try:
    while True:
        time.sleep(0.2)
except KeyboardInterrupt:
    print("\nEncerrado.")
finally:
    for m in ins:
        m.close_port()

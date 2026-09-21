#!/usr/bin/env python3
# Backend Linux (evdev + uinput) del puente para teclado partido.
# Lee las mitades por USB, comparte una sola pila de capas y emite por un teclado
# virtual. La distribucion se toma de un .vil de Vial.
#
#   sudo python3 corne_bridge_linux.py --vil ../keymaps/example_dvorak.vil
#   sudo python3 corne_bridge_linux.py --vil TU.vil --test     # solo diagnostico

import os
import sys
import time
import argparse
import selectors

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import bridge_core as core

try:
    from evdev import InputDevice, UInput, list_devices, ecodes as e
except ImportError:
    sys.exit("Falta python3-evdev.  Instala:  sudo apt install python3-evdev")

RESCAN = 3.0

class LinuxBackend:
    def __init__(self):
        caps = set()
        for name in core.QMK2EV.values():
            caps.add(getattr(e, name))
        self.ui = UInput({e.EV_KEY: sorted(caps)}, name='corne-usb-bridge')
    def press(self, name):   self.ui.write(e.EV_KEY, getattr(e, name), 1); self.ui.syn()
    def release(self, name): self.ui.write(e.EV_KEY, getattr(e, name), 0); self.ui.syn()
    def close(self):         self.ui.close()

def build_raw2pos(km):
    r2p = {}
    for pos, name in enumerate(km['raw_names']):
        r2p[getattr(e, name)] = pos
    return r2p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vil', required=True, help='keymap .vil de Vial')
    ap.add_argument('--vendor', default='0x4653', help='USB vendor id (hex). Corne = 0x4653')
    ap.add_argument('--tapping-term', type=float, default=core.TAPPING_TERM)
    ap.add_argument('--test', action='store_true', help='solo imprime que tecla llega')
    args = ap.parse_args()
    vendor = int(args.vendor, 16)

    km = core.load_vil(args.vil)
    raw2pos = build_raw2pos(km)
    backend = None if args.test else LinuxBackend()
    eng = core.Engine(km['layers'], backend, args.tapping_term) if not args.test else None

    sel = selectors.DefaultSelector()
    active = {}
    next_scan = 0.0
    print('corne-usb-bridge (Linux)%s. Ctrl+C para salir.' % (' [--test]' if args.test else ''))
    try:
        while True:
            now = time.monotonic()
            if now >= next_scan:
                next_scan = now + RESCAN
                for path in list_devices():
                    if path in active:
                        continue
                    try:
                        d = InputDevice(path)
                    except OSError:
                        continue
                    if d.info.vendor != vendor:
                        d.close(); continue
                    caps = d.capabilities().get(e.EV_KEY, [])
                    if not any(c in raw2pos for c in caps):
                        d.close(); continue
                    try:
                        d.grab(); sel.register(d, selectors.EVENT_READ); active[path] = d
                        print('Mitad conectada:', path)
                    except OSError:
                        d.close()
            if eng:
                eng.expire()
            waits = [eng.next_timeout() if eng else None, next_scan - time.monotonic()]
            timeout = max(0.0, min(w for w in waits if w is not None))
            for key, _ in sel.select(timeout):
                d = key.fileobj
                try:
                    for ev in d.read():
                        if ev.type != e.EV_KEY or ev.code not in raw2pos:
                            continue
                        pos = raw2pos[ev.code]
                        if args.test:
                            if ev.value == 1:
                                side = 'IZQ' if pos < km['n_left'] else 'DER'
                                print('%s  pos=%-2d  base=%s' % (side, pos, km['layers'][0][pos]))
                        elif ev.value == 1:
                            eng.key_down(pos)
                        elif ev.value == 0:
                            eng.key_up(pos)
                except OSError:
                    try: sel.unregister(d)
                    except Exception: pass
                    try: d.ungrab()
                    except Exception: pass
                    active.pop(d.path, None)
                    print('Mitad desconectada:', d.path)
    except KeyboardInterrupt:
        if eng: eng.cleanup()
        for d in active.values():
            try: d.ungrab()
            except OSError: pass
        if backend: backend.close()

if __name__ == '__main__':
    main()

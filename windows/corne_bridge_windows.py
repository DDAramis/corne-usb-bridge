#!/usr/bin/env python3
# Backend Windows (EXPERIMENTAL, sin probar en hardware real).
# Usa la libreria `keyboard` (pip install keyboard) con un hook global. Como en
# "modo crudo" la mano izquierda manda A.. y la derecha F1.., se distinguen por el
# propio codigo, sin necesidad de identificar el dispositivo.
#
#   pip install keyboard
#   python  corne_bridge_windows.py --vil ..\keymaps\example_dvorak.vil
#   (ejecutar como Administrador para que el hook pueda bloquear teclas)
#
# Limitaciones conocidas: el hook global de `keyboard` reinyecta eventos; se
# mitiga con un contador de eventos propios, pero para algo 100% robusto conviene
# el driver Interception (ver README). Se agradecen PRs de quien tenga Windows.

import os
import sys
import time
import argparse
import threading
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import bridge_core as core

try:
    import keyboard
except ImportError:
    sys.exit("Falta la libreria `keyboard`.  Instala:  pip install keyboard")

# nombre canonico KEY_* -> nombre de la libreria `keyboard`
WIN = {
    'KEY_TAB':'tab','KEY_ESC':'esc','KEY_ENTER':'enter','KEY_BACKSPACE':'backspace',
    'KEY_SPACE':'space','KEY_MINUS':'-','KEY_EQUAL':'=','KEY_LEFTBRACE':'[',
    'KEY_RIGHTBRACE':']','KEY_BACKSLASH':'\\','KEY_SEMICOLON':';','KEY_APOSTROPHE':"'",
    'KEY_GRAVE':'`','KEY_COMMA':',','KEY_DOT':'.','KEY_SLASH':'/','KEY_102ND':'<',
    'KEY_LEFTSHIFT':'shift','KEY_RIGHTSHIFT':'right shift','KEY_LEFTCTRL':'ctrl',
    'KEY_RIGHTCTRL':'right ctrl','KEY_LEFTALT':'alt','KEY_RIGHTALT':'alt gr',
    'KEY_LEFTMETA':'windows','KEY_RIGHTMETA':'windows','KEY_UP':'up','KEY_DOWN':'down',
    'KEY_LEFT':'left','KEY_RIGHT':'right','KEY_HOME':'home','KEY_END':'end',
    'KEY_PAGEUP':'page up','KEY_PAGEDOWN':'page down','KEY_DELETE':'delete',
    'KEY_INSERT':'insert','KEY_VOLUMEUP':'volume up','KEY_VOLUMEDOWN':'volume down',
    'KEY_MUTE':'volume mute','KEY_NEXTSONG':'next track','KEY_PREVIOUSSONG':'previous track',
    'KEY_PLAYPAUSE':'play/pause media','KEY_SCROLLLOCK':'scroll lock','KEY_PAUSE':'pause',
    'KEY_SYSRQ':'print screen','KEY_CAPSLOCK':'caps lock','KEY_KPPLUS':'add',
    'KEY_KPASTERISK':'multiply','KEY_KPMINUS':'subtract','KEY_KPSLASH':'divide',
    'KEY_KPENTER':'enter','KEY_KPDOT':'decimal',
}
for _c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    WIN['KEY_' + _c] = _c.lower()
for _d in '1234567890':
    WIN['KEY_' + _d] = _d
for _i in range(1, 25):
    WIN['KEY_F%d' % _i] = 'f%d' % _i

class WindowsBackend:
    def __init__(self):
        self.injected = Counter()
        self.lock = threading.Lock()
    def _emit(self, name, down):
        win = WIN.get(name)
        if not win:
            return
        with self.lock:
            self.injected[(down, win)] += 1
        (keyboard.press if down else keyboard.release)(win)
    def press(self, name):   self._emit(name, True)
    def release(self, name): self._emit(name, False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vil', required=True)
    ap.add_argument('--tapping-term', type=float, default=core.TAPPING_TERM)
    ap.add_argument('--test', action='store_true')
    args = ap.parse_args()

    km = core.load_vil(args.vil)
    raw2pos = {}                                  # nombre `keyboard` -> posicion
    for pos, kname in enumerate(km['raw_names']):
        raw2pos[WIN[kname]] = pos

    backend = WindowsBackend()
    eng = None if args.test else core.Engine(km['layers'], backend, args.tapping_term)

    def on_event(ev):
        key = (ev.event_type == 'down', ev.name)
        if not args.test:                          # ignora nuestros propios eventos
            with backend.lock:
                if backend.injected.get(key, 0) > 0:
                    backend.injected[key] -= 1
                    return True
        pos = raw2pos.get(ev.name)
        if pos is None:
            return True                            # tecla ajena: pasa tal cual
        if args.test:
            if ev.event_type == 'down':
                side = 'IZQ' if pos < km['n_left'] else 'DER'
                print('%s  pos=%-2d  base=%s' % (side, pos, km['layers'][0][pos]))
        elif ev.event_type == 'down':
            eng.key_down(pos)
        else:
            eng.key_up(pos)
        return False                               # bloquea el codigo crudo

    keyboard.hook(on_event, suppress=True)
    print('corne-usb-bridge (Windows, EXPERIMENTAL)%s. Ctrl+C para salir.'
          % (' [--test]' if args.test else ''))
    try:
        while True:
            if eng:
                eng.expire()
            time.sleep(0.005)
    except KeyboardInterrupt:
        if eng:
            eng.cleanup()
        keyboard.unhook_all()

if __name__ == '__main__':
    main()

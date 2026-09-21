# rgb.py — control de RGB por HID (mismo canal que Vial), a las DOS mitades.
# Protocolo tomado de vial-gui (editor/rgb_configurator.py, protocol/keyboard_comm.py).
# EXPERIMENTAL: sin cable entre mitades, cada mitad tiene su RGB; esto manda la
# misma orden a las dos para que vayan sincronizadas y para que la capa RGB del
# teclado funcione en vivo a traves del puente.

import glob
import os
import struct

CMD_SET = 0x07
CMD_SAVE = 0x09
# QMK RGBLIGHT (underglow)
RGBLIGHT_BRIGHT = 0x80
RGBLIGHT_EFFECT = 0x81
RGBLIGHT_SPEED  = 0x82
RGBLIGHT_COLOR  = 0x83
# VialRGB (matriz por-tecla)
VIALRGB_SET_MODE = 0x41

VENDOR = 0x4653

def _linux_nodes():
    nodes = []
    for h in sorted(glob.glob('/sys/class/hidraw/hidraw*')):
        dev = os.path.join(h, 'device')
        try:
            if ('%04X' % VENDOR) not in open(os.path.join(dev, 'uevent')).read().upper():
                continue
            rd = open(os.path.join(dev, 'report_descriptor'), 'rb').read()
        except Exception:
            continue
        if b'\x06\x60\xff' in rd:                 # Usage Page 0xFF60 = interfaz Vial
            nodes.append('/dev/' + os.path.basename(h))
    return nodes

def _open_writers():
    """Devuelve callables write(payload) para cada mitad. Linux: hidraw crudo."""
    writers = []
    for path in _linux_nodes():
        try:
            fd = os.open(path, os.O_RDWR)
        except OSError:
            continue
        def make(fd):
            def w(body):
                buf = body + bytes(32 - len(body))
                for b in (b'\x00' + buf, buf):
                    try:
                        os.write(fd, b); return
                    except OSError:
                        pass
            return w
        writers.append(make(fd))
    if writers:
        return writers
    # Windows / otros: intentar hidapi
    try:
        import hid
        for d in hid.enumerate(VENDOR, 0):
            if d.get('usage_page') == 0xFF60:
                dev = hid.device(); dev.open_path(d['path'])
                writers.append(lambda body, dev=dev: dev.write(b'\x00' + body + bytes(32 - len(body))))
    except Exception:
        pass
    return writers

def clamp(x):
    return max(0, min(255, x))

class RGB:
    def __init__(self, system='rgblight'):
        self.system = system            # 'rgblight' o 'vialrgb'
        self.writers = _open_writers()
        self.enabled = True
        self.bright = 200
        self.hue = 0
        self.sat = 255
        self.effect = 1                 # rgblight: 1=solido ; vialrgb: 2=solido
        self.speed = 128
        self.apply()

    def _send(self, body):
        for w in self.writers:
            w(body)

    def apply(self):
        if self.system == 'vialrgb':
            mode = self.effect if self.enabled else 0
            self._send(struct.pack("<BBHBBBB", CMD_SET, VIALRGB_SET_MODE, mode,
                                   self.speed, self.hue, self.sat, self.bright))
        else:
            self._send(struct.pack(">BBB", CMD_SET, RGBLIGHT_EFFECT, self.effect if self.enabled else 0))
            self._send(struct.pack(">BBB", CMD_SET, RGBLIGHT_BRIGHT, self.bright if self.enabled else 0))
            self._send(struct.pack(">BBBB", CMD_SET, RGBLIGHT_COLOR, self.hue, self.sat))

    def save(self):
        self._send(struct.pack(">B", CMD_SAVE))

    def handle(self, name):
        """Aplica un keycode RGB_* del teclado."""
        if name == 'RGB_TOG':
            self.enabled = not self.enabled
        elif name in ('RGB_VAI',):
            self.bright = clamp(self.bright + 17)
        elif name in ('RGB_VAD',):
            self.bright = clamp(self.bright - 17)
        elif name in ('RGB_HUI',):
            self.hue = (self.hue + 17) % 256
        elif name in ('RGB_HUD',):
            self.hue = (self.hue - 17) % 256
        elif name in ('RGB_SAI',):
            self.sat = clamp(self.sat + 17)
        elif name in ('RGB_SAD',):
            self.sat = clamp(self.sat - 17)
        elif name in ('RGB_SPI',):
            self.speed = clamp(self.speed + 17)
        elif name in ('RGB_SPD',):
            self.speed = clamp(self.speed - 17)
        elif name in ('RGB_MOD',):
            self.effect += 1
        elif name in ('RGB_RMOD',):
            self.effect = max(0, self.effect - 1)
        else:
            return
        self.apply()

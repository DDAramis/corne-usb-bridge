# rgb.py — control de RGB por HID (mismo canal que Vial), a las DOS mitades.
# Protocolo tomado de vial-gui (editor/rgb_configurator.py, protocol/keyboard_comm.py).
#
# Compatible con Vial: abre y CIERRA el canal HID en cada orden, para no
# retener el dispositivo. Asi el matrix tester y editar en Vial siguen funcionando
# con el puente en marcha. Sin cable entre mitades cada una tiene su RGB; mandamos
# la misma orden a las dos para que vayan sincronizadas.

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

def _win_paths():
    try:
        import hid
    except Exception:
        return []
    return [d['path'] for d in hid.enumerate(VENDOR, 0) if d.get('usage_page') == 0xFF60]

def clamp(x):
    return max(0, min(255, x))

class RGB:
    def __init__(self, system='rgblight'):
        self.system = system            # 'rgblight' (underglow) o 'vialrgb' (matriz)
        self.nodes = _linux_nodes()
        self.win_paths = [] if self.nodes else _win_paths()
        self.enabled = True
        self.bright = 200
        self.hue = 0
        self.sat = 255
        self.effect = 1                 # rgblight: 1=solido ; vialrgb: 2=solido
        self.speed = 128
        self.apply()

    @staticmethod
    def _write(writer, body):
        buf = body + bytes(32 - len(body))
        for b in (b'\x00' + buf, buf):
            try:
                writer(b); return
            except Exception:
                pass

    def _send(self, body):
        for path in self.nodes:                       # Linux: hidraw crudo, abrir/cerrar
            try:
                fd = os.open(path, os.O_RDWR)
            except OSError:
                continue
            try:
                self._write(lambda b: os.write(fd, b), body)
            finally:
                os.close(fd)
        for path in self.win_paths:                   # Windows: hidapi, abrir/cerrar
            try:
                import hid
                dev = hid.device(); dev.open_path(path)
            except Exception:
                continue
            try:
                self._write(dev.write, body)
            finally:
                try: dev.close()
                except Exception: pass

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
        elif name == 'RGB_VAI':
            self.bright = clamp(self.bright + 17)
        elif name == 'RGB_VAD':
            self.bright = clamp(self.bright - 17)
        elif name == 'RGB_HUI':
            self.hue = (self.hue + 17) % 256
        elif name == 'RGB_HUD':
            self.hue = (self.hue - 17) % 256
        elif name == 'RGB_SAI':
            self.sat = clamp(self.sat + 17)
        elif name == 'RGB_SAD':
            self.sat = clamp(self.sat - 17)
        elif name == 'RGB_SPI':
            self.speed = clamp(self.speed + 17)
        elif name == 'RGB_SPD':
            self.speed = clamp(self.speed - 17)
        elif name == 'RGB_MOD':
            self.effect += 1
        elif name == 'RGB_RMOD':
            self.effect = max(0, self.effect - 1)
        else:
            return
        self.apply()

# bridge_core.py  —  logica compartida (sin dependencias de SO)
# Lee un keymap de Vial (.vil) y ofrece un motor que reproduce Dvorak/QWERTY +
# capas + mod-taps + layer-taps, para un teclado partido cuyas mitades llegan por
# USB separadas. Los backends (Linux/Windows) solo aportan leer teclas y emitirlas.
#
# Modelo: cada mitad se pone en "modo crudo" (make_raw_vil.py) y manda codigos
# unicos:  mano izquierda -> A..  ;  mano derecha -> F1..  . El motor los traduce
# a la distribucion real del .vil, compartiendo una sola pila de capas entre ambas.

import json
import time

TAPPING_TERM = 0.20      # s: mantener mas de esto = hold (mod o capa)

# QMK keycode -> nombre canonico evdev (KEY_*). Los backends traducen desde aqui.
QMK2EV = {
    'TAB':'KEY_TAB','SCOLON':'KEY_SEMICOLON','COMMA':'KEY_COMMA','DOT':'KEY_DOT',
    'P':'KEY_P','Y':'KEY_Y','ESCAPE':'KEY_ESC','A':'KEY_A','O':'KEY_O','E':'KEY_E',
    'U':'KEY_U','I':'KEY_I','QUOTE':'KEY_APOSTROPHE','Q':'KEY_Q','J':'KEY_J',
    'K':'KEY_K','X':'KEY_X','SPACE':'KEY_SPACE','BSPACE':'KEY_BACKSPACE','L':'KEY_L',
    'R':'KEY_R','C':'KEY_C','G':'KEY_G','F':'KEY_F','MINUS':'KEY_MINUS','S':'KEY_S',
    'N':'KEY_N','T':'KEY_T','H':'KEY_H','D':'KEY_D','SLASH':'KEY_SLASH','Z':'KEY_Z',
    'V':'KEY_V','W':'KEY_W','M':'KEY_M','B':'KEY_B','ENTER':'KEY_ENTER',
    'LSHIFT':'KEY_LEFTSHIFT','LGUI':'KEY_LEFTMETA','LALT':'KEY_LEFTALT',
    'RALT':'KEY_RIGHTALT','LCTL':'KEY_LEFTCTRL','RSFT':'KEY_RIGHTSHIFT',
    'RCTL':'KEY_RIGHTCTRL','RGUI':'KEY_RIGHTMETA','RSHIFT':'KEY_RIGHTSHIFT',
    'SCROLLLOCK':'KEY_SCROLLLOCK','PAUSE':'KEY_PAUSE','VOLD':'KEY_VOLUMEDOWN',
    'VOLU':'KEY_VOLUMEUP','UP':'KEY_UP','DOWN':'KEY_DOWN','LEFT':'KEY_LEFT',
    'RIGHT':'KEY_RIGHT','HOME':'KEY_HOME','END':'KEY_END','PGUP':'KEY_PAGEUP',
    'PGDOWN':'KEY_PAGEDOWN','DELETE':'KEY_DELETE','INSERT':'KEY_INSERT',
    'MNXT':'KEY_NEXTSONG','MPRV':'KEY_PREVIOUSSONG','MPLY':'KEY_PLAYPAUSE',
    'MUTE':'KEY_MUTE','LBRACKET':'KEY_LEFTBRACE','RBRACKET':'KEY_RIGHTBRACE',
    'NONUS_BSLASH':'KEY_102ND','NUBS':'KEY_102ND','BSLASH':'KEY_BACKSLASH',
    'GRAVE':'KEY_GRAVE','EQUAL':'KEY_EQUAL','PSCREEN':'KEY_SYSRQ','CAPS':'KEY_CAPSLOCK',
    '1':'KEY_1','2':'KEY_2','3':'KEY_3','4':'KEY_4','5':'KEY_5','6':'KEY_6',
    '7':'KEY_7','8':'KEY_8','9':'KEY_9','0':'KEY_0',
    'KP_PLUS':'KEY_KPPLUS','KP_ASTERISK':'KEY_KPASTERISK','KP_MINUS':'KEY_KPMINUS',
    'KP_SLASH':'KEY_KPSLASH','KP_ENTER':'KEY_KPENTER','KP_DOT':'KEY_KPDOT',
}
MODS = {'LSHIFT','LGUI','LALT','RALT','LCTL','RSFT','RCTL','RGUI','RSHIFT'}
RGB_PREFIX = ('RGB_', 'RGBLIGHT_')      # se controlan por HID (ver rgb.py)
IGNORE_PREFIX = ('BL_',)
IGNORE = {'RESET', 'QK_BOOT', 'KC_NO', 'DB_TOGG', 'EE_CLR'}

def name_of(kc):
    suf = kc[3:] if kc.startswith('KC_') else kc
    if suf not in QMK2EV:
        raise KeyError('keycode sin traducir: %s' % kc)
    return QMK2EV[suf]

def parse(s):
    """action string de Vial -> tupla canonica (con nombres KEY_*)."""
    if s.startswith(RGB_PREFIX):
        return ('rgb', s)
    if s in ('KC_NO', 'KC_NONE') or s in IGNORE or s.startswith(IGNORE_PREFIX):
        return ('none',)
    if s in ('KC_TRNS', 'KC_TRANSPARENT', '_______'):
        return ('trans',)
    if s.startswith('LT') and s[2:3].isdigit():
        return ('lt', int(s[2:s.index('(')]), name_of(s[s.index('(') + 1:-1]))
    if s.startswith('MO('):
        return ('mo', int(s[3:-1]))
    if s.startswith('LCTL_T('):
        return ('mt', 'KEY_LEFTCTRL', name_of(s[7:-1]))
    if s.startswith('RCTL_T('):
        return ('mt', 'KEY_RIGHTCTRL', name_of(s[7:-1]))
    if s.startswith('LSFT_T('):
        return ('mt', 'KEY_LEFTSHIFT', name_of(s[7:-1]))
    if s.startswith('RSFT_T('):
        return ('mt', 'KEY_RIGHTSHIFT', name_of(s[7:-1]))
    if s.startswith('LALT_T('):
        return ('mt', 'KEY_LEFTALT', name_of(s[7:-1]))
    if s.startswith('LGUI_T('):
        return ('mt', 'KEY_LEFTMETA', name_of(s[7:-1]))
    if s.startswith('LSFT('):
        return ('combo', 'KEY_LEFTSHIFT', name_of(s[5:-1]))
    if s.startswith('RALT('):
        return ('combo', 'KEY_RIGHTALT', name_of(s[5:-1]))
    if s.startswith('LCTL('):
        return ('combo', 'KEY_LEFTCTRL', name_of(s[5:-1]))
    suf = s[3:] if s.startswith('KC_') else s
    return ('mod', name_of(s)) if suf in MODS else ('key', name_of(s))

# --- Codigos crudos (lo que manda cada mitad en "modo crudo") ----------------
LEFT_RAW = ['KEY_' + c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
RIGHT_RAW = ['KEY_F%d' % i for i in range(1, 25)]

def load_vil(path):
    """Lee un .vil y devuelve la estructura para el motor y para make_raw_vil.
       Asume teclado partido con la matriz dividida por la mitad (p.ej. Corne)."""
    data = json.load(open(path))
    layout = data['layout']                        # [capa][fila][col]
    rows0 = layout[0]
    half = len(rows0) // 2                          # filas de la mano izquierda

    positions = []                                  # (fila, col) de cada tecla fisica
    for ri, row in enumerate(rows0):
        for ci, cell in enumerate(row):
            if cell != -1:
                positions.append((ri, ci))
    left_positions = [p for p in positions if p[0] < half]
    n_left = len(left_positions)

    layers = []
    for layer in layout:
        flat = [layer[ri][ci] for (ri, ci) in positions]
        layers.append(flat)

    raw_names, raw_by_cell = [], {}
    for idx, (ri, ci) in enumerate(positions):
        if ri < half:
            name = LEFT_RAW[idx]
        else:
            name = RIGHT_RAW[idx - n_left]
        raw_names.append(name)
        raw_by_cell[(ri, ci)] = name

    return {
        'data': data, 'layout': layout, 'half': half,
        'positions': positions, 'layers': layers,
        'raw_names': raw_names, 'raw_by_cell': raw_by_cell, 'n_left': n_left,
    }

class Engine:
    """Motor de teclado: capas, mod-tap, layer-tap, transparencias.
       backend debe implementar press(name) y release(name) con nombres KEY_*."""
    def __init__(self, layers, backend, tapping_term=TAPPING_TERM):
        self.layers = layers
        self.backend = backend
        self.tt = tapping_term
        self.stack = [0]
        self.held = {}
        self.pending = {}

    def resolve(self, pos):
        for layer in reversed(self.stack):
            s = self.layers[layer][pos]
            if s in ('KC_TRNS', 'KC_TRANSPARENT', '_______'):
                continue
            return parse(s)
        return ('none',)

    def _apply_hold(self, pos, act):
        if act[0] == 'lt':
            self.stack.append(act[1]); self.held[pos] = ('layer', act[1])
        elif act[0] == 'mt':
            self.backend.press(act[1]); self.held[pos] = ('mod', act[1])

    def _force_holds(self):
        for pos in list(self.pending):
            act, _ = self.pending.pop(pos)
            self._apply_hold(pos, act)

    def key_down(self, pos):
        if self.pending:
            self._force_holds()                      # otra tecla => tap-hold pasan a hold
        act = self.resolve(pos)
        k = act[0]
        if k in ('lt', 'mt'):
            self.pending[pos] = (act, time.monotonic() + self.tt)
        elif k == 'mo':
            self.stack.append(act[1]); self.held[pos] = ('layer', act[1])
        elif k in ('key', 'mod'):
            self.backend.press(act[1]); self.held[pos] = ('key', act[1])
        elif k == 'combo':
            self.backend.press(act[1]); self.backend.press(act[2])
            self.held[pos] = ('combo', act[1], act[2])
        elif k == 'rgb':
            rgb = getattr(self.backend, 'rgb', None)     # RGB por HID (opcional)
            if rgb:
                rgb(act[1])

    def key_up(self, pos):
        if pos in self.pending:
            act, _ = self.pending.pop(pos)           # se solto rapido => tap
            self.backend.press(act[2]); self.backend.release(act[2])
            return
        kind = self.held.pop(pos, None)
        if not kind:
            return
        if kind[0] == 'layer':
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i] == kind[1]:
                    del self.stack[i]; break
        elif kind[0] == 'combo':
            self.backend.release(kind[2]); self.backend.release(kind[1])
        else:
            self.backend.release(kind[1])

    def expire(self):
        now = time.monotonic()
        for pos, (act, dl) in list(self.pending.items()):
            if dl <= now:
                self.pending.pop(pos); self._apply_hold(pos, act)

    def next_timeout(self):
        if not self.pending:
            return None
        return max(0.0, min(dl for _, dl in self.pending.values()) - time.monotonic())

    def cleanup(self):
        for pos in list(self.held):
            self.key_up(pos)

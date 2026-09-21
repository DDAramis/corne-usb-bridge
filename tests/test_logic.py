#!/usr/bin/env python3
# Pruebas de la logica pura (sin SO, sin hardware). Corre en cualquier sistema
# y en Docker.  python3 tests/test_logic.py
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import bridge_core as core

VIL = os.path.join(os.path.dirname(__file__), '..', 'keymaps', 'example_dvorak.vil')

class Rec:                     # backend de prueba: apunta lo que se emite
    def __init__(self): self.out = []
    def press(self, n):   self.out.append(('+', n))
    def release(self, n): self.out.append(('-', n))

def test_load_and_parse():
    km = core.load_vil(VIL)
    assert len(km['layers'][0]) == 42, 'esperadas 42 teclas'
    assert km['n_left'] == 21
    for layer in km['layers']:
        for s in layer:
            core.parse(s)                       # no debe lanzar KeyError

def test_tap_hold_and_layers():
    km = core.load_vil(VIL)
    b = Rec(); eng = core.Engine(km['layers'], b)
    # una tecla normal (posicion 7 = KC_A en base) emite KEY_A
    eng.key_down(7); eng.key_up(7)
    assert ('+', 'KEY_A') in b.out and ('-', 'KEY_A') in b.out
    # pila de capas vuelve a base tras soltar todo
    for p in range(42):
        eng.key_down(p); eng.key_up(p)
    assert eng.stack == [0], 'la pila de capas debe volver a [0]'
    assert not eng.held and not eng.pending

def test_raw_roundtrip():
    km = core.load_vil(VIL)
    # cada posicion tiene un codigo crudo unico
    assert len(set(km['raw_names'])) == 42

if __name__ == '__main__':
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print('OK', name); n += 1
    print('%d pruebas OK' % n)

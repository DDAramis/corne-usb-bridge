#!/usr/bin/env python3
# Modo "nativo, sin software": genera dos .vil (uno por mano) para que CADA mitad
# escriba su lado correctamente ella sola, sin el puente y sin el cable entre
# mitades. Funciona en TODO (disco encriptado, login, escritorio), pero las capas
# que cruzan de una mano a la otra dejan de funcionar (la base Dvorak/QWERTY y los
# mod-taps de cada mano si funcionan).
#
#   python3 make_native_vil.py TU.vil
#   -> TU.native_left.vil (mitad izquierda)  y  TU.native_right.vil (mitad derecha)
#
# Ambas mitades se creen "master izquierda", asi que las dos leen las filas de la
# izquierda de la matriz: a la derecha le reubicamos ahi su propia mitad.

import sys
import copy
import json
import argparse

import bridge_core as core

def build_right(km):
    layout = km['layout']; half = km['half']; src0 = layout[0]; n_rows = len(src0)
    out = []
    for layer in layout:
        new = []
        for ri in range(n_rows):
            if ri < half:
                new.append(list(layer[half + ri]))               # su mitad, en filas master
            else:
                new.append([-1 if c == -1 else 'KC_NO' for c in src0[ri]])
        out.append(new)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vil')
    args = ap.parse_args()
    km = core.load_vil(args.vil)
    base = args.vil[:-4] if args.vil.endswith('.vil') else args.vil

    left = copy.deepcopy(km['data'])                              # izquierda = original
    json.dump(left, open(base + '.native_left.vil', 'w'))
    print('creado:', base + '.native_left.vil')

    right = copy.deepcopy(km['data']); right['layout'] = build_right(km)
    json.dump(right, open(base + '.native_right.vil', 'w'))
    print('creado:', base + '.native_right.vil')

if __name__ == '__main__':
    main()

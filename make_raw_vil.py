#!/usr/bin/env python3
# Genera los keymaps "crudos" por mano a partir de un .vil normal.
# Cada mitad, sin el cable entre ellas, se cree "master izquierda", asi que las
# dos usan las filas de la izquierda de la matriz. Para distinguirlas cargamos un
# archivo distinto en cada una: la izquierda manda A.. y la derecha F1..
# (colocadas de forma que respeten la posicion original de la mano derecha).
#
#   python3 make_raw_vil.py TU.vil
#   -> crea TU.raw_left.vil  y  TU.raw_right.vil
#
# Carga TU.raw_left.vil en la mitad IZQUIERDA y TU.raw_right.vil en la DERECHA
# (con Vial, una mitad cada vez).

import sys
import copy
import json
import argparse

import bridge_core as core

def kc(name):                       # KEY_A -> KC_A ;  KEY_F1 -> KC_F1
    return 'KC_' + name[4:]

def build(km, side):
    layout = km['layout']
    half = km['half']
    src0 = layout[0]
    n_rows = len(src0)
    out = []
    for li in range(len(layout)):
        layer = []
        for ri in range(n_rows):
            row = []
            for ci, cell in enumerate(src0[ri]):
                if cell == -1:
                    row.append(-1)
                elif li != 0 or ri >= half:
                    row.append('KC_NO')                 # capas altas / filas no-master
                elif side == 'left':
                    row.append(kc(km['raw_by_cell'][(ri, ci)]))
                else:                                    # right: mano derecha en filas master
                    mirror = (half + ri, ci)
                    row.append(kc(km['raw_by_cell'][mirror])
                               if mirror in km['raw_by_cell'] else 'KC_NO')
            layer.append(row)
        out.append(layer)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vil', help='keymap .vil de Vial (tu distribucion normal)')
    args = ap.parse_args()

    km = core.load_vil(args.vil)
    base = args.vil[:-4] if args.vil.endswith('.vil') else args.vil
    for side, suffix in (('left', 'raw_left'), ('right', 'raw_right')):
        data = copy.deepcopy(km['data'])
        data['layout'] = build(km, side)
        path = '%s.%s.vil' % (base, suffix)
        json.dump(data, open(path, 'w'))
        print('creado:', path)

if __name__ == '__main__':
    main()

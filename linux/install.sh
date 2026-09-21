#!/usr/bin/env bash
# Instalador para Linux (systemd). Uso:
#   sudo ./install.sh /ruta/a/tu.vil
set -euo pipefail

if [[ $EUID -ne 0 ]]; then echo "Ejecuta con sudo: sudo ./install.sh TU.vil"; exit 1; fi
VIL="${1:-}"
if [[ -z "$VIL" || ! -f "$VIL" ]]; then echo "Falta el .vil:  sudo ./install.sh /ruta/a/tu.vil"; exit 1; fi

SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST=/opt/corne-usb-bridge

echo ">> Dependencia python3-evdev"
if ! python3 -c "import evdev" 2>/dev/null; then
  apt-get update && apt-get install -y python3-evdev
fi

echo ">> Copiando a $DEST"
mkdir -p "$DEST"
cp -r "$SRC"/. "$DEST"/
cp "$VIL" "$DEST/keymaps/user.vil"

echo ">> Generando keymaps crudos por mano"
( cd "$DEST" && python3 make_raw_vil.py keymaps/user.vil )

echo ">> Instalando servicio systemd"
install -m644 "$DEST/linux/corne-bridge.service" /etc/systemd/system/corne-usb-bridge.service
systemctl daemon-reload
systemctl enable --now corne-usb-bridge.service

cat <<EOF

Listo. El servicio 'corne-usb-bridge' esta activo y arranca solo.

FALTA UN PASO MANUAL (una vez), en Vial:
  - Carga en la mitad IZQUIERDA:  $DEST/keymaps/user.raw_left.vil
  - Carga en la mitad DERECHA:    $DEST/keymaps/user.raw_right.vil

Estado:   systemctl status corne-usb-bridge.service
Diagnostico de teclas:
  sudo systemctl stop corne-usb-bridge.service
  sudo python3 $DEST/linux/corne_bridge_linux.py --vil $DEST/keymaps/user.vil --test
EOF

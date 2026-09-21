# corne-usb-bridge

**Your split keyboard's inter-half port (TRRS) died? Keep using it.**

If the connector that links the two halves of your split keyboard (Corne / crkbd
and similar) breaks, you can plug **each half into the computer by its own USB
cable** and this tool makes them behave like one keyboard again — reproducing your
**exact Vial layout**: Dvorak/QWERTY base, all layers, mod-taps and layer-taps,
with **layer state shared across both halves** (which is the part a plain
two-independent-halves setup loses).

It is, essentially, *your QMK layout running on the host*.

> Built after the TRRS jack on a Corne broke. Linux is tested and used daily.
> Windows is experimental (see below). Contributions welcome.

---

## Why this is needed

A split keyboard normally links its halves over a TRRS/serial cable: one half is
"master" (USB to PC), the other is "slave", and they **share state** (active layer,
modifiers) over that cable. If that link breaks and you just plug both halves in
separately, each half becomes its own master — so the base letters work, but any
**layer key on one half no longer affects the other half** (e.g. a layer with
arrows on the right, toggled from a thumb key on the left, stops working).

This tool moves that "shared state" job to the computer.

> ⚠️ You **cannot** fix this by joining the two halves' USB‑C ports with a C‑to‑C
> cable — those are host ports; at best nothing happens, at worst you short VBUS.
> (Some *new* boards, e.g. splitkb's Halcyon series, do use a dedicated USB‑C link
> between halves — that's different hardware, wired for it.)

## How it works

1. Each half is flashed (via Vial, no re-compile) with a **"raw" keymap** so every
   physical key sends a unique code: **left half → `A..U`, right half → `F1..F21`**.
   `make_raw_vil.py` generates these two `.vil` files from *your* normal `.vil`
   (keeping your keyboard's UID, so Vial accepts them).
2. A host program grabs both halves, runs a **layer/tap-hold engine** built from
   your real `.vil`, and emits the final keystrokes through a virtual keyboard.
   Because it sees both halves at once, **layers are shared again**.

Your OS keyboard layout stays whatever it was (the tool emits the same HID codes
your firmware did; the OS applies the layout).

## Requirements

- Your Vial `.vil` layout file.
- **Linux:** `python3` + `python3-evdev`.
- **Windows (experimental):** `python` + `pip install keyboard`.

## Install — Linux (tested)

```bash
git clone https://github.com/DDAramis/corne-usb-bridge
cd corne-usb-bridge
sudo linux/install.sh /path/to/your.vil
```

This installs a systemd service (auto-starts on boot, restarts on crash,
hot-plug aware) and generates the two raw `.vil` files. Then, **once**, in Vial:

- load `…/keymaps/user.raw_left.vil` into the **left** half,
- load `…/keymaps/user.raw_right.vil` into the **right** half
  (plug one half at a time so Vial talks to the right one).

Diagnose which key is which without emitting anything:

```bash
sudo systemctl stop corne-usb-bridge.service
sudo python3 linux/corne_bridge_linux.py --vil keymaps/your.vil --test
```

## Install — Windows (experimental, untested on real hardware)

**Don't run it in a foreground terminal for daily use** — a plain
`python …corne_bridge_windows.py` keeps running *inside* that terminal, so the
window has to stay open **and** you can't type into that terminal (it's busy
running the bridge). Run it **in the background** instead:

- **Recommended — install + auto-start (background, elevated):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\windows\install_autostart.ps1
  ```
- **Or start it in the background manually** (run the .bat as Administrator):
  `windows\run_bridge.bat`  — stop it with `windows\stop_bridge.bat`.
- **Foreground, only for diagnostics** (blocks the terminal, `Ctrl+C` to quit):
  ```powershell
  python windows\corne_bridge_windows.py --vil keymaps\example_dvorak.vil --test
  ```

Must run **as Administrator** (the global hook needs it to suppress/emit keys),
with the OS keyboard layout set to the one your `.vil` targets. The Windows
backend uses a global `keyboard` hook; it works because the two halves send
distinct codes (`A..` vs `F1..`). For rock-solid behavior in every window
(including elevated apps and consoles), the
[Interception](https://github.com/oblitum/Interception) driver is the recommended
path (PRs welcome).

**Auto-start on Windows** (equivalent to the systemd service) — run as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\install_autostart.ps1
```

This installs the dependencies, registers a Scheduled Task that launches the
bridge at every logon with admin rights, **and starts it immediately** (no
reboot needed). Note: on Windows this covers the **desktop** (after your user
logs in), not the Windows lock/login screen (session-0 isolation) — unlike
Linux, which covers the greeter too.

## RGB / lights (experimental)

The RGB layer keys (`RGB_TOG`, `RGB_HUI`, brightness, effect…) are sent to **both
halves at once** over the same HID channel Vial uses, so the lights react live and
stay in sync. Protocol taken from
[vial-gui](https://github.com/vial-kb/vial-gui) (`editor/rgb_configurator.py`,
`protocol/keyboard_comm.py`): `CMD_VIA_LIGHTING_SET_VALUE (0x07)` + QMK RGBLIGHT
value ids (`0x80` brightness, `0x81` effect, `0x83` hue/sat), or VialRGB
(`0x41 set mode`). Test which one your board uses with `sudo python3 rgb_test.py`.
Set the system with `CORNE_RGB=rgblight|vialrgb`.

## Use your own keyboard / layout

Point everything at your own `.vil`. The tool assumes a split whose matrix is
split in half by rows (true for Corne/crkbd). Other splits may need small tweaks
to `load_vil()` in `bridge_core.py`.

## Docker (logic only)

```bash
docker build -t corne-usb-bridge .     # runs the pure-logic tests
```

Docker reproducibly validates the **parsing + layer/tap-hold engine** on any OS.
It does **not** run the actual bridge: capturing/emitting keys needs real USB
devices and OS input APIs (evdev/uinput on Linux, a global hook on Windows), which
a container doesn't have — and Linux containers can't run the Windows backend.

## Limitations

- While the bridge isn't running, the keyboard types the **raw codes** (letters/F).
  The service keeps it running; if you want the keyboard "native" again, reload
  your normal `.vil` (but then cross-half layers are gone).
- **RGB** is driven over HID (see the RGB section) — experimental. If it does
  nothing, your board may use a different lighting system; try `rgb_test.py`.
- **USB-C cables:** each half needs a **data** USB-C cable, not a charge-only one.
  A charge-only cable powers the LEDs but the PC won't detect the keyboard (it
  won't show in `lsusb`). Any "sync & charge" / USB-2.0 data cable works.
- Tap-hold resolves as *hold on other key press* (tune `TAPPING_TERM` in
  `bridge_core.py`).
- The OS keyboard layout must stay the one your `.vil` was designed for.

## Prior art / alternatives

This is a niche, `.vil`-driven convenience wrapper. The general idea — remap and
add layers on the **host**, merging several keyboards — is already done, and very
well, by mature cross-platform tools:

- **[kanata](https://github.com/jtroo/kanata)** — cross-platform (Linux/macOS/Windows)
  remapper in Rust with layers, tap-hold, macros; can manage multiple keyboards.
- **[kmonad](https://github.com/kmonad/kmonad)** — the original (Haskell) that
  inspired kanata.
- On Linux also `keyd`, `xremap`.

If you're comfortable hand-writing a config, **kanata is likely the more robust
choice**. The point of `corne-usb-bridge` is that it reads your existing Vial
`.vil` directly and auto-generates the per-hand "raw" keymaps for the specific
"my split's TRRS broke" situation — no config to write.

## License

MIT © 2026 Aramis Jakolic

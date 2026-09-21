@echo off
REM Lanza el puente en Windows. Edita la ruta del .vil si hace falta.
cd /d "%~dp0.."
python windows\corne_bridge_windows.py --vil keymaps\example_dvorak.vil

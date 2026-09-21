@echo off
REM Lanza el puente en SEGUNDO PLANO (sin ventana, no ocupa el terminal).
REM  -> Puedes cerrar esta ventana y seguir escribiendo en el terminal.
REM Ejecutar COMO ADMINISTRADOR (clic derecho > Ejecutar como administrador),
REM si no, el hook no puede bloquear/emitir teclas.
cd /d "%~dp0.."
start "" pythonw windows\corne_bridge_windows.py --vil keymaps\example_dvorak.vil
echo Puente lanzado en segundo plano. Ya puedes cerrar esta ventana.
echo Para pararlo:  windows\stop_bridge.bat

@echo off
REM Detiene el puente en segundo plano.
schtasks /end /tn "corne-usb-bridge" >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
echo Puente detenido.

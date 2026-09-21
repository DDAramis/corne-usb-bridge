# install_autostart.ps1 — instala y deja funcionando el puente en Windows.
# Instala dependencias, registra el autoarranque (Tarea Programada al iniciar
# sesion, con admin) Y LO ARRANCA YA — no hay que esperar a reiniciar.
#
# Ejecutar como Administrador:
#   powershell -ExecutionPolicy Bypass -File .\install_autostart.ps1
#
# Nota: en Windows el autoarranque llega hasta el ESCRITORIO (tras iniciar tu
# sesion), no a la pantalla de login/bloqueo de Windows (aislamiento de sesion 0).

$ErrorActionPreference = "Stop"
$root   = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root "windows\corne_bridge_windows.py"
$vil    = Join-Path $root "keymaps\example_dvorak.vil"

Write-Host ">> Instalando dependencias (keyboard, hidapi)..."
python -m pip install --upgrade keyboard hidapi | Out-Null

$py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python).Source }

$action    = New-ScheduledTaskAction -Execute $py -Argument "`"$script`" --vil `"$vil`""
$trigger   = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
                -ExecutionTimeLimit ([TimeSpan]::Zero)

Write-Host ">> Registrando autoarranque..."
Register-ScheduledTask -TaskName "corne-usb-bridge" -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Host ">> Arrancandolo ahora..."
Start-ScheduledTask -TaskName "corne-usb-bridge"

Write-Host ""
Write-Host "Listo. El puente esta corriendo YA y arrancara solo en cada inicio de sesion."
Write-Host "Quitar autoarranque:  Unregister-ScheduledTask -TaskName corne-usb-bridge -Confirm:`$false"

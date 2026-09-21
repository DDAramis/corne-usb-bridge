# install_autostart.ps1 — autoarranque del puente en Windows.
# Crea una Tarea Programada que lo lanza al INICIAR SESION con permisos de admin
# (el hook global los necesita). Es el equivalente al servicio systemd de Linux.
#
# Ejecutar como Administrador:
#   powershell -ExecutionPolicy Bypass -File .\install_autostart.ps1
#
# Nota: en Windows el autoarranque llega hasta el ESCRITORIO (tras iniciar tu
# sesion), no a la pantalla de login/bloqueo de Windows (aislamiento de sesion 0).

$ErrorActionPreference = "Stop"
$root   = Split-Path -Parent $PSScriptRoot
$py     = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python).Source }
$script = Join-Path $root "windows\corne_bridge_windows.py"
$vil    = Join-Path $root "keymaps\example_dvorak.vil"

$action    = New-ScheduledTaskAction -Execute $py -Argument "`"$script`" --vil `"$vil`""
$trigger   = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "corne-usb-bridge" -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Listo. El puente arrancara solo al iniciar sesion (con permisos de admin)."
Write-Host "Arrancarlo ya:      Start-ScheduledTask -TaskName corne-usb-bridge"
Write-Host "Quitar autoarranque: Unregister-ScheduledTask -TaskName corne-usb-bridge -Confirm:`$false"

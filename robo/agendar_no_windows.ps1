# Cria (ou recria) as duas tarefas do Agendador do Windows que perguntam se o usuario quer atualizar o
# Portal Fiscal (ver iniciar_com_windows.py). Rodar uma vez, no PowerShell, dentro da pasta robo:
#     powershell -ExecutionPolicy Bypass -File agendar_no_windows.ps1
# Para remover:  Unregister-ScheduledTask -TaskName "Portal Fiscal*" -Confirm:$false

$robo = $PSScriptRoot
$pythonw = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = (Get-Command pythonw).Source }
$script = Join-Path $robo "iniciar_com_windows.py"
$usuario = "$env:USERDOMAIN\$env:USERNAME"

$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited

# 1) Ao entrar no Windows (1 minuto depois); o script so pergunta na primeira vez do dia, em dia util
$gatilhoLogon = New-ScheduledTaskTrigger -AtLogOn -User $usuario
$gatilhoLogon.Delay = "PT1M"
$acaoLogon = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$script`" --logon" -WorkingDirectory $robo
Register-ScheduledTask -TaskName "Portal Fiscal - ao entrar no Windows" -Trigger $gatilhoLogon `
    -Action $acaoLogon -Settings $config -Principal $principal -Force | Out-Null

# 2) Dias uteis as 13:10
$gatilho1310 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "13:10"
$acao1310 = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$script`" --horario" -WorkingDirectory $robo
Register-ScheduledTask -TaskName "Portal Fiscal - 13h10" -Trigger $gatilho1310 `
    -Action $acao1310 -Settings $config -Principal $principal -Force | Out-Null

Get-ScheduledTask -TaskName "Portal Fiscal*" | Format-Table TaskName, State

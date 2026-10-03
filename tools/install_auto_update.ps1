param(
    [Parameter(Mandatory = $true)][string]$Python,
    [string]$Repo = (Join-Path (Split-Path $PSScriptRoot -Parent) '..\pokeblack-integration')
)
$ErrorActionPreference = 'Stop'
$taskName = 'pokeblack progress updater'
$sitePath = Split-Path $PSScriptRoot -Parent
$taskPythonPath = (Resolve-Path -LiteralPath $Python).Path
if ([IO.Path]::GetFileName($taskPythonPath) -ne 'pythonw.exe') { throw 'Use pythonw.exe so updates run without a console window.' }
$sourcePath = (Resolve-Path -LiteralPath $Repo).Path
$scriptPath = Join-Path $PSScriptRoot 'auto_update.py'
$logPath = Join-Path $sitePath '.cache\auto-update.log'
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask -and -not $existingTask.Actions.Arguments.Contains($scriptPath)) { throw 'An unrelated task already uses this name; preserving it.' }
$arguments = '"{0}" --repo "{1}" --log "{2}"' -f $scriptPath,$sourcePath,$logPath
$action = New-ScheduledTaskAction -Execute $taskPythonPath -Argument $arguments -WorkingDirectory $sitePath
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$taskUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Publish progress metadata after a new pokeblack main build is verified and published. Checks every five minutes while signed in.' -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Output "Installed $taskName; checks every five minutes while this user is signed in."

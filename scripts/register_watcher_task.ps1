$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File d:\be-yours-mylab\scripts\anythingllm_watcher.ps1'

$trigger = New-ScheduledTaskTrigger -AtLogOn -User 'startec'

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal -UserId 'startec' -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName 'AnythingLLM Watcher' `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Get-ScheduledTask -TaskName 'AnythingLLM Watcher' | Format-List TaskName, State, Triggers

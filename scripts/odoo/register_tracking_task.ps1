# Enregistre la tache planifiee Windows qui pousse l'export Station vers le VPS
# et declenche l'envoi des mails de tracking DPD (vps_notify_tracking.py --send).
# Repete toutes les heures de 09h a 20h. Idempotent cote VPS (dedup colis).

$ErrorActionPreference = "Stop"
$TaskName = "MyLab - Notif tracking DPD"
$Python   = "C:\Users\startec\AppData\Local\Programs\Python\Python312\python.exe"
$WorkDir  = "d:\be-yours-mylab"

$action = New-ScheduledTaskAction -Execute $Python `
    -Argument "-m scripts.odoo.station_upload_to_vps" -WorkingDirectory $WorkDir

# Declencheur : tous les jours a 09:00, repete chaque heure pendant 11h (-> 20:00)
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00am
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At 9:00am `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Hours 11)).Repetition

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

# Tourne sous le compte courant, quand l'utilisateur est connecte (acces reseau + fichiers)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Pousse l'export Station du jour vers le VPS et envoie les mails de tracking DPD (idempotent)." `
    -Force | Out-Null

Write-Host "Tache enregistree : $TaskName"
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State | Format-Table -AutoSize
$ti = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host ("Prochaine execution : " + $ti.NextRunTime)

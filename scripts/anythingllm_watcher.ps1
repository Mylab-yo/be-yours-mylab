# ---------------------------------------------------------------------------
# Watcher : declenche le sync Obsidian -> AnythingLLM quand AnythingLLM
# demarre. Tourne en arriere-plan depuis l'ouverture de session Windows
# (planifie via Task Scheduler avec trigger AtLogOn).
#
# Polling toutes les 15s. Detecte les transitions not-running -> running.
# Cooldown 60 min entre 2 declenchements.
#
# Logs : %LOCALAPPDATA%\anythingllm-sync\watcher.log
# ---------------------------------------------------------------------------

$LogDir = Join-Path $env:LOCALAPPDATA 'anythingllm-sync'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir 'watcher.log'
$LastFiredFile = Join-Path $LogDir 'watcher.last-fired'

$SyncBat = 'd:\be-yours-mylab\scripts\sync_anythingllm.bat'
$PollSec = 15
$CooldownMin = 60

function Write-Log($msg) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Add-Content -Path $Log -Value $line -Encoding UTF8
}

Write-Log "Watcher started (PID $PID)"

$wasRunning = $false

while ($true) {
    try {
        $proc = Get-Process AnythingLLM -ErrorAction SilentlyContinue
        $isRunning = ($proc -ne $null)

        if ($isRunning -and -not $wasRunning) {
            $pidList = ($proc.Id -join ',')
            Write-Log "AnythingLLM detecte (PID $pidList)"

            $fire = $true
            if (Test-Path $LastFiredFile) {
                $lastFired = Get-Content $LastFiredFile -ErrorAction SilentlyContinue
                if ($lastFired) {
                    try {
                        $lastDt = [DateTime]::Parse($lastFired)
                        $minSince = ((Get-Date) - $lastDt).TotalMinutes
                        if ($minSince -lt $CooldownMin) {
                            $msg = "Cooldown actif ({0:N0} min depuis dernier fire, seuil {1}) - skip" -f $minSince, $CooldownMin
                            Write-Log $msg
                            $fire = $false
                        }
                    } catch {
                        # Parse failed, fire anyway
                    }
                }
            }

            if ($fire) {
                Start-Sleep -Seconds 20
                Write-Log "Lancement du sync via $SyncBat"
                Start-Process -FilePath $SyncBat -WindowStyle Hidden
                (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | Set-Content -Path $LastFiredFile -Encoding UTF8
            }
        } elseif (-not $isRunning -and $wasRunning) {
            Write-Log "AnythingLLM ferme"
        }

        $wasRunning = $isRunning
    } catch {
        Write-Log ("Erreur boucle : " + $_.Exception.Message)
    }
    Start-Sleep -Seconds $PollSec
}

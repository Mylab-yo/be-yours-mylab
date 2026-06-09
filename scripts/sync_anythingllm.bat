@echo off
REM ---------------------------------------------------------------------------
REM Wrapper pour Windows Task Scheduler.
REM Sync quotidien du vault Obsidian vers AnythingLLM.
REM - Lance AnythingLLM Desktop si pas demarre
REM - Attend que le serveur :3001 reponde (jusqu'a 90s)
REM - Lance le sync, log tout
REM
REM Logs dans %LOCALAPPDATA%\anythingllm-sync\last-run.log
REM ---------------------------------------------------------------------------

set LOGDIR=%LOCALAPPDATA%\anythingllm-sync
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set LOG=%LOGDIR%\last-run.log
set ALLM_EXE=C:\Users\startec\AppData\Local\Programs\AnythingLLM\AnythingLLM.exe
set OLLAMA_APP=C:\Users\startec\AppData\Local\Programs\Ollama\ollama app.exe

echo. >> "%LOG%"
echo ============================================ >> "%LOG%"
echo === Sync started %DATE% %TIME% >> "%LOG%"
echo ============================================ >> "%LOG%"

REM Check if Ollama is running, launch if not. AnythingLLM crashe sans Ollama.
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if errorlevel 1 (
    echo Ollama pas demarre, lancement... >> "%LOG%"
    start "" "%OLLAMA_APP%"
    REM Wait up to 30s for Ollama to be ready on :11434
    set /a OTRIES=0
    :WAITOLLAMA
    set /a OTRIES+=1
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=2).read()" 2>nul
    if not errorlevel 1 goto :OLLAMA_OK
    if %OTRIES% GEQ 15 (
        echo ATTENTION : Ollama toujours down apres 30s, AnythingLLM va crash. >> "%LOG%"
        goto :OLLAMA_OK
    )
    timeout /t 2 /nobreak >nul
    goto :WAITOLLAMA
    :OLLAMA_OK
    echo Ollama pret apres %OTRIES% essais. >> "%LOG%"
) else (
    echo Ollama deja demarre. >> "%LOG%"
)

REM Check if AnythingLLM is running, launch if not
tasklist /FI "IMAGENAME eq AnythingLLM.exe" 2>nul | find /I "AnythingLLM.exe" >nul
if errorlevel 1 (
    echo AnythingLLM pas demarre, lancement... >> "%LOG%"
    start "" "%ALLM_EXE%"
) else (
    echo AnythingLLM deja demarre. >> "%LOG%"
)

REM Wait up to 90s for the API server to respond on :3001
set /a TRIES=0
:WAITLOOP
set /a TRIES+=1
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3001/api/ping', timeout=2).read()" 2>nul
if not errorlevel 1 (
    echo Serveur :3001 OK apres %TRIES% essais. >> "%LOG%"
    goto :RUNSYNC
)
if %TRIES% GEQ 30 (
    echo ECHEC : serveur :3001 toujours down apres 90s. Abort. >> "%LOG%"
    exit /b 2
)
timeout /t 3 /nobreak >nul
goto :WAITLOOP

:RUNSYNC
python d:\be-yours-mylab\scripts\sync_obsidian_to_anythingllm.py --verbose >> "%LOG%" 2>&1
set EXITCODE=%ERRORLEVEL%

echo === Sync finished %DATE% %TIME% (exit=%EXITCODE%) >> "%LOG%"

exit /b %EXITCODE%

@echo off
REM ---------------------------------------------------------------------------
REM Wrapper pour Windows Task Scheduler.
REM Sync quotidien du vault Obsidian vers AnythingLLM.
REM Logs dans %LOCALAPPDATA%\anythingllm-sync\last-run.log
REM ---------------------------------------------------------------------------

set LOGDIR=%LOCALAPPDATA%\anythingllm-sync
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set LOG=%LOGDIR%\last-run.log

echo. >> "%LOG%"
echo ============================================ >> "%LOG%"
echo === Sync started %DATE% %TIME% >> "%LOG%"
echo ============================================ >> "%LOG%"

python d:\be-yours-mylab\scripts\sync_obsidian_to_anythingllm.py --verbose >> "%LOG%" 2>&1
set EXITCODE=%ERRORLEVEL%

echo === Sync finished %DATE% %TIME% (exit=%EXITCODE%) >> "%LOG%"

exit /b %EXITCODE%

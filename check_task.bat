@echo off
setlocal enabledelayedexpansion
set MAX_CHECKS=15
set CHECK_COUNT=0

:loop
set /a CHECK_COUNT+=1
echo Check %CHECK_COUNT%/%MAX_CHECKS%: Looking for task_complete.txt...

if exist task_complete.txt (
    echo.
    echo === File found! Contents: ===
    type task_complete.txt
    echo.
    echo Loop completed successfully.
    goto :end
)

if %CHECK_COUNT% geq %MAX_CHECKS% (
    echo.
    echo === LIMIT HIT: Checked %MAX_CHECKS% times, file never appeared ===
    goto :end
)

echo Not found yet. Waiting 60 seconds...
timeout /t 60 /nobreak >nul
goto :loop

:end
endlocal

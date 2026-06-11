@echo off
REM ====================================================================
REM  Goertzel_AGI - one-click launcher for Windows
REM  Double-click this file to start the cognition dashboard.
REM ====================================================================
title Goertzel_AGI
echo Starting Goertzel_AGI ...
echo.

where py >/dev/null 2>/dev/null
if %errorlevel%==0 (
    set PYTHON=py
) else (
    where python >/dev/null 2>/dev/null
    if %errorlevel%==0 (
        set PYTHON=python
    ) else (
        echo Python was not found. Please install Python 3.10+ from
        echo https://www.python.org/downloads/  and try again.
        pause
        exit /b 1
    )
)

echo Open your browser at  http://localhost:8000
echo (Close this window to stop the server.)
echo.
%PYTHON% -m webui.server
pause

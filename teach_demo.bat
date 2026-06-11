@echo off
REM Load the demo knowledge pack into a persistent store (data/atomspace.json)
title Goertzel_AGI - teach demo
where py >/dev/null 2>/dev/null && (set PYTHON=py) || (set PYTHON=python)
%PYTHON% -m goertzel_agi.teach knowledge/demo
echo.
echo Done. Start the dashboard with start.bat to explore what it learned.
pause

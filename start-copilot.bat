@echo off
rem Double-click to start the DC Exception Copilot: the API, the Streamlit UI and your browser.
rem Close this window (or press Ctrl+C) to stop everything.
title DC Exception Copilot
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo uv is not installed or not on PATH. Install it from https://docs.astral.sh/uv/
    pause
    exit /b 1
)

rem Already running? Then just open the page.
curl -s -o nul http://localhost:8501 && (
    echo The copilot is already running.
    if not defined COPILOT_NO_BROWSER start "" http://localhost:8501
    exit /b 0
)

echo Starting the API on http://localhost:8000 ...
rem "python -m" avoids the small .exe launchers that Windows application control can block.
rem /b keeps the API in this window, so closing the window stops it too.
start /b "" uv run python -m uvicorn copilot.api.app:app --port 8000

set /a tries=0
:wait_api
rem ping is a wait that works with or without an interactive console
ping -n 2 127.0.0.1 >nul
curl -s -o nul http://localhost:8000/health && goto api_ready
set /a tries+=1
if %tries% lss 60 goto wait_api
echo The API did not start within 60 seconds - see the messages above.
pause
exit /b 1

:api_ready
echo.
echo   Chat UI:   http://localhost:8501   (opening in your browser)
echo   API docs:  http://localhost:8000/docs
echo   Close this window to stop the copilot.
echo.
if not defined COPILOT_NO_BROWSER start "" cmd /c "ping -n 5 127.0.0.1 >nul & start http://localhost:8501"
uv run --group ui python -m streamlit run src/copilot/ui/streamlit_app.py

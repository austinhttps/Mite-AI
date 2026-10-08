@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" desktop_assistant.py %*
) else (
    python desktop_assistant.py %*
)

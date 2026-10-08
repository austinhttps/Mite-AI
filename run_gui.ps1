# Launch Native Desktop Assistant GUI
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPy = Join-Path $ScriptDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPy) {
    & $VenvPy (Join-Path $ScriptDir "gui_assistant.py") @args
} else {
    python (Join-Path $ScriptDir "gui_assistant.py") @args
}

param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

& $PythonExe -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    & $PythonExe -m pip install pyinstaller --quiet
}

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name LimpiarAxess `
    main.py

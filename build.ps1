param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$ProjectRoot = $PSScriptRoot
$EntryPoint = Join-Path $ProjectRoot "main.py"
$IconPath = Join-Path $ProjectRoot "limpiar.ico"

if (-not (Test-Path $EntryPoint)) {
    throw "No se encontró el archivo de entrada: $EntryPoint"
}

if (-not (Test-Path $IconPath)) {
    throw "No se encontró el icono requerido: $IconPath"
}

& $PythonExe -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    & $PythonExe -m pip install pyinstaller --quiet
}

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --distpath $ProjectRoot `
    --workpath (Join-Path $ProjectRoot "build") `
    --specpath $ProjectRoot `
    --name LimpiarAxess `
    --icon $IconPath `
    $EntryPoint

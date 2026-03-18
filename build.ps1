param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$ProjectRoot = $PSScriptRoot
$EntryPoint = Join-Path $ProjectRoot "main.py"
$IconPath = Join-Path $ProjectRoot "limpiar.ico"
$BuildRequirements = Join-Path $ProjectRoot "requirements-build.txt"
$VersionInfoPath = Join-Path $ProjectRoot ".pyi_build\\version_info.txt"
$OutputExe = Join-Path $ProjectRoot "LimpiarAxess.exe"

if (-not (Test-Path $EntryPoint)) {
    throw "No se encontró el archivo de entrada: $EntryPoint"
}

if (-not (Test-Path $IconPath)) {
    throw "No se encontró el icono requerido: $IconPath"
}

if (Test-Path $BuildRequirements) {
    & $PythonExe -m pip install -r $BuildRequirements --quiet
} else {
    & $PythonExe -m pip install pyinstaller --quiet
}

& $PythonExe .\scripts\generate_version_resource.py $VersionInfoPath

if (Test-Path $OutputExe) {
    Remove-Item $OutputExe -Force
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
    --version-file $VersionInfoPath `
    $EntryPoint

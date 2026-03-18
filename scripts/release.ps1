param(
    [ValidateSet("major", "minor", "patch")]
    [string]$Bump = "patch",
    [Parameter(Mandatory = $true)]
    [string]$Message,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $ProjectRoot

$NewVersion = (& $PythonExe .\scripts\bump_version.py $Bump).Trim()
if (-not $NewVersion) {
    throw "No se pudo calcular la nueva versión."
}

& $PythonExe -m unittest discover -s tests -p "test_*.py"
if ($LASTEXITCODE -ne 0) {
    throw "Las pruebas fallaron. Se cancela el release."
}

& .\build.ps1 -PythonExe $PythonExe
if ($LASTEXITCODE -ne 0) {
    throw "La compilación falló. Se cancela el release."
}

git rev-parse --verify --quiet "refs/tags/v$NewVersion" *> $null
if ($LASTEXITCODE -eq 0) {
    throw "La etiqueta v$NewVersion ya existe."
}

git add -A
git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo crear el commit."
}

git tag -a "v$NewVersion" -m "Release v$NewVersion"
git push origin main
git push origin "v$NewVersion"

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SelectedPython = (pyenv which python).Trim()

Push-Location (Join-Path $RepositoryRoot "core")
try {
    poetry env use $SelectedPython
    poetry install --no-interaction
    poetry run pytest --cov=tlefinder.core --cov=tlefinder.benchmarks --cov-report=term-missing
    poetry build
}
finally {
    Pop-Location
}

Push-Location (Join-Path $RepositoryRoot "api")
try {
    poetry env use $SelectedPython
    poetry install --no-interaction
    poetry run pytest --cov=tlefinder.api --cov-report=term-missing
    poetry build
}
finally {
    Pop-Location
}

$CoreWheel = Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot "core/dist") -Filter "*.whl"
$ApiWheel = Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot "api/dist") -Filter "*.whl"
$Wheels = @($CoreWheel.FullName) + @($ApiWheel.FullName)
& $SelectedPython (Join-Path $PSScriptRoot "inspect_wheels.py") @Wheels

$Npm = if ($IsWindows) { "npm.cmd" } else { "npm" }
Push-Location (Join-Path $RepositoryRoot "gui")
try {
    & $Npm ci
    & $Npm test
    & $Npm run typecheck
    & $Npm run build
}
finally {
    Pop-Location
}

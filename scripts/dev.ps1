<#
.SYNOPSIS
Starts the TLE Finder API and GUI together for local development.

.DESCRIPTION
Runs Uvicorn on http://127.0.0.1:2626 and Vite on
http://127.0.0.1:2627. Both processes share this terminal and are stopped
when the launcher exits or Ctrl+C is pressed.
#>

[CmdletBinding()]
param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$ApiDirectory = Join-Path $RepositoryRoot "api"
$GuiDirectory = Join-Path $RepositoryRoot "gui"
$ApiPort = 2626
$GuiPort = 2627
$IsWindowsHost = $env:OS -eq "Windows_NT"

function Resolve-RequiredCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$InstallHint
    )

    $Command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $Command) {
        throw "Required command '$Name' was not found. $InstallHint"
    }

    if ($Command.Source) {
        return $Command.Source
    }
    return $Command.Path
}

function Assert-PortAvailable {
    param(
        [Parameter(Mandatory)]
        [int]$Port,

        [Parameter(Mandatory)]
        [string]$Service
    )

    $Listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        $Port
    )
    try {
        $Listener.Start()
    }
    catch [System.Net.Sockets.SocketException] {
        throw "Port $Port is already in use and is required by $Service. Stop the other local server or run 'docker compose down' first."
    }
    finally {
        $Listener.Stop()
    }
}

function Stop-DevelopmentProcess {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Name
    )

    if ($null -eq $Process) {
        return
    }

    $Process.Refresh()
    if ($Process.HasExited) {
        return
    }

    Write-Host "Stopping $Name..." -ForegroundColor DarkGray
    if ($IsWindowsHost) {
        & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null
    }
    else {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

$Poetry = Resolve-RequiredCommand -Name "poetry" -InstallHint "Install Poetry and run 'poetry install' from the api directory."
$NpmName = if ($IsWindowsHost) { "npm.cmd" } else { "npm" }
$Npm = Resolve-RequiredCommand -Name $NpmName -InstallHint "Install Node.js and run 'npm ci' from the gui directory."

if (-not (Test-Path -LiteralPath (Join-Path $ApiDirectory "pyproject.toml"))) {
    throw "API project not found at $ApiDirectory."
}
if (-not (Test-Path -LiteralPath (Join-Path $GuiDirectory "package.json"))) {
    throw "GUI project not found at $GuiDirectory."
}

Assert-PortAvailable -Port $ApiPort -Service "the API"
Assert-PortAvailable -Port $GuiPort -Service "the GUI"

$ApiArguments = @(
    "run",
    "uvicorn",
    "tlefinder.api.app:app",
    "--host",
    "127.0.0.1",
    "--port",
    $ApiPort
)
if (-not $NoReload) {
    $ApiArguments += "--reload"
}

$GuiArguments = @(
    "run",
    "dev",
    "--",
    "--host",
    "127.0.0.1",
    "--port",
    $GuiPort,
    "--strictPort"
)

$ApiProcess = $null
$GuiProcess = $null

try {
    Write-Host "Starting TLE Finder API on http://127.0.0.1:$ApiPort..." -ForegroundColor Cyan
    $ApiProcess = Start-Process -FilePath $Poetry -ArgumentList $ApiArguments -WorkingDirectory $ApiDirectory -NoNewWindow -PassThru

    Start-Sleep -Milliseconds 500
    $ApiProcess.Refresh()
    if ($ApiProcess.HasExited) {
        throw "The API exited during startup with code $($ApiProcess.ExitCode)."
    }

    Write-Host "Starting TLE Finder GUI on http://127.0.0.1:$GuiPort..." -ForegroundColor Cyan
    $GuiProcess = Start-Process -FilePath $Npm -ArgumentList $GuiArguments -WorkingDirectory $GuiDirectory -NoNewWindow -PassThru

    Write-Host "TLE Finder is starting. Press Ctrl+C to stop both services." -ForegroundColor Green

    while ($true) {
        Start-Sleep -Milliseconds 500
        $ApiProcess.Refresh()
        $GuiProcess.Refresh()

        if ($ApiProcess.HasExited) {
            throw "The API exited unexpectedly with code $($ApiProcess.ExitCode)."
        }
        if ($GuiProcess.HasExited) {
            throw "The GUI exited unexpectedly with code $($GuiProcess.ExitCode)."
        }
    }
}
finally {
    Stop-DevelopmentProcess -Process $GuiProcess -Name "GUI"
    Stop-DevelopmentProcess -Process $ApiProcess -Name "API"
}

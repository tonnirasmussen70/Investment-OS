[CmdletBinding()]
param(
    [string]$RepositoryPath = (Join-Path $PSScriptRoot "..\.."),
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "Jarvis.Windows.ps1")

Assert-JarvisWindows
$RepositoryPath = (Resolve-Path -LiteralPath $RepositoryPath).Path
if (-not $ConfigPath) {
    $ConfigPath = Join-Path (Get-JarvisDefaultRuntimeRoot) "jarvis.env"
}

$settings = Import-JarvisEnvironment -ConfigPath $ConfigPath
Assert-JarvisEnvironment -Settings $settings
$pythonPath = Get-JarvisPythonPath -RepositoryPath $RepositoryPath
$bindAddress = $settings["JARVIS_BIND_HOST"]
$port = $settings["JARVIS_PORT"]
$runtimeRoot = Split-Path -Parent $ConfigPath
$serviceLogPath = Join-Path $runtimeRoot "service.log"

for ($index = 2; $index -ge 1; $index--) {
    $source = "$serviceLogPath.$index"
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        Move-Item -LiteralPath $source -Destination "$serviceLogPath.$($index + 1)" -Force
    }
}
if (Test-Path -LiteralPath $serviceLogPath -PathType Leaf) {
    Move-Item -LiteralPath $serviceLogPath -Destination "$serviceLogPath.1" -Force
}

Set-Location -LiteralPath $RepositoryPath
& $pythonPath -m uvicorn api.app:app `
    --host $bindAddress `
    --port $port `
    --workers 1 `
    --no-access-log *>> $serviceLogPath

if ($LASTEXITCODE -ne 0) {
    Add-Content -LiteralPath $serviceLogPath -Value "Jarvis API exited with code $LASTEXITCODE."
    throw "Jarvis API exited with code $LASTEXITCODE."
}

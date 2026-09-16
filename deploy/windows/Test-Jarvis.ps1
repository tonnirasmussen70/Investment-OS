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
$baseUrl = "http://127.0.0.1:$($settings['JARVIS_PORT'])"
[Environment]::SetEnvironmentVariable("JARVIS_BASE_URL", $baseUrl, "Process")

Set-Location -LiteralPath $RepositoryPath
& $pythonPath scripts\smoke_test_jarvis_api.py

if ($LASTEXITCODE -ne 0) {
    throw "Jarvis smoke test failed with code $LASTEXITCODE."
}

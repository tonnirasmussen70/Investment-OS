[CmdletBinding()]
param(
    [string]$RepositoryPath = (Join-Path $PSScriptRoot "..\.."),
    [string]$RuntimeRoot = "",
    [string]$TaskName = "InvestmentOS-Jarvis"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "Jarvis.Windows.ps1")

function New-JarvisToken {
    $bytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($bytes)
}

function Get-ExistingValue {
    param(
        [hashtable]$Settings,
        [string]$Name,
        [string]$DefaultValue
    )
    if ($Settings.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace($Settings[$Name])) {
        return $Settings[$Name]
    }
    return $DefaultValue
}

Assert-JarvisWindows
$RepositoryPath = (Resolve-Path -LiteralPath $RepositoryPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $RepositoryPath "api\app.py") -PathType Leaf)) {
    throw "RepositoryPath does not contain the Jarvis API."
}
if (-not $RuntimeRoot) {
    $RuntimeRoot = Get-JarvisDefaultRuntimeRoot
}
$RuntimeRoot = [IO.Path]::GetFullPath($RuntimeRoot)

$auditDirectory = Join-Path $RuntimeRoot "audit"
$configPath = Join-Path $RuntimeRoot "jarvis.env"
$snapshotPath = Join-Path $RepositoryPath "data\portfolio_snapshot.json"
$startScript = Join-Path $PSScriptRoot "Start-Jarvis.ps1"
$testScript = Join-Path $PSScriptRoot "Test-Jarvis.ps1"
$venvPath = Join-Path $RepositoryPath ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
New-Item -ItemType Directory -Path $auditDirectory -Force | Out-Null

$existing = @{}
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    $existing = Import-JarvisEnvironment -ConfigPath $configPath
}
$token = Get-ExistingValue -Settings $existing -Name "JARVIS_API_TOKEN" -DefaultValue (New-JarvisToken)
$rateLimit = Get-ExistingValue -Settings $existing -Name "JARVIS_RATE_LIMIT_PER_MINUTE" -DefaultValue "60"
$maxBytes = Get-ExistingValue -Settings $existing -Name "JARVIS_AUDIT_MAX_BYTES" -DefaultValue "10485760"
$backupCount = Get-ExistingValue -Settings $existing -Name "JARVIS_AUDIT_BACKUP_COUNT" -DefaultValue "7"
$port = Get-ExistingValue -Settings $existing -Name "JARVIS_PORT" -DefaultValue "8000"
$auditPath = Join-Path $auditDirectory "jarvis_audit.jsonl"

$configuration = @(
    "JARVIS_ENV=production",
    "JARVIS_API_TOKEN=$token",
    "JARVIS_RATE_LIMIT_PER_MINUTE=$rateLimit",
    "JARVIS_AUDIT_LOG=$auditPath",
    "JARVIS_AUDIT_PERSISTENT=true",
    "JARVIS_AUDIT_MAX_BYTES=$maxBytes",
    "JARVIS_AUDIT_BACKUP_COUNT=$backupCount",
    "INVESTMENT_OS_SNAPSHOT=$snapshotPath",
    "JARVIS_BIND_HOST=127.0.0.1",
    "JARVIS_PORT=$port"
)
$userId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$temporaryConfigPath = Join-Path $RuntimeRoot ([IO.Path]::GetRandomFileName())
try {
    $configuration | Set-Content -LiteralPath $temporaryConfigPath -Encoding UTF8
    & icacls.exe $temporaryConfigPath "/inheritance:r" "/grant:r" "${userId}:(F)" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not restrict access to the Jarvis configuration file."
    }

    $settings = Import-JarvisEnvironment -ConfigPath $temporaryConfigPath
    Assert-JarvisEnvironment -Settings $settings
    Move-Item -LiteralPath $temporaryConfigPath -Destination $configPath -Force
}
catch {
    if (Test-Path -LiteralPath $temporaryConfigPath) {
        Remove-Item -LiteralPath $temporaryConfigPath -Force
    }
    throw
}

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    $environmentCreated = $false
    $pyLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & $pyLauncher.Source -3.12 -m venv $venvPath
        $environmentCreated = $LASTEXITCODE -eq 0
        if (-not $environmentCreated) {
            & $pyLauncher.Source -3.11 -m venv $venvPath
            $environmentCreated = $LASTEXITCODE -eq 0
        }
    }
    if (-not $environmentCreated) {
        $systemPython = Get-Command "python.exe" -ErrorAction SilentlyContinue
        if (-not $systemPython) {
            throw "Python 3.11 or newer is required."
        }
        & $systemPython.Source -m venv $venvPath
        $environmentCreated = $LASTEXITCODE -eq 0
    }
    if (-not $environmentCreated) {
        throw "Could not create the Jarvis virtual environment."
    }
}

& $pythonPath -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Jarvis requires Python 3.11 or newer."
}
& $pythonPath -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Could not upgrade pip."
}
& $pythonPath -m pip install -r (Join-Path $RepositoryPath "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Could not install Jarvis dependencies."
}
& $pythonPath -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "Jarvis dependencies are inconsistent."
}
& $pythonPath -m compileall -q `
    (Join-Path $RepositoryPath "api") `
    (Join-Path $RepositoryPath "jarvis") `
    (Join-Path $RepositoryPath "scripts")
if ($LASTEXITCODE -ne 0) {
    throw "Jarvis Python sources did not compile."
}

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
}

$powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$actionArguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$startScript`" -RepositoryPath `"$RepositoryPath`" -ConfigPath `"$configPath`""
$action = New-ScheduledTaskAction `
    -Execute $powerShellPath `
    -Argument $actionArguments `
    -WorkingDirectory $RepositoryPath
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal `
    -UserId $userId `
    -LogonType Interactive `
    -RunLevel Limited
$taskSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable
$task = New-ScheduledTask `
    -Action $action `
    -Principal $principal `
    -Settings $taskSettings `
    -Trigger $trigger
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

$healthy = $false
$healthUrl = "http://127.0.0.1:$port/healthz"
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $response = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 2
        if ($response.status -eq "ok") {
            $healthy = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $healthy) {
    throw "Jarvis did not become healthy within 30 seconds."
}

& $testScript -RepositoryPath $RepositoryPath -ConfigPath $configPath
if ($LASTEXITCODE -ne 0) {
    throw "Jarvis smoke test failed after installation."
}

Write-Host "Jarvis is installed and ready at http://127.0.0.1:$port"
Write-Host "Scheduled task: $TaskName"
Write-Host "Configuration: $configPath"

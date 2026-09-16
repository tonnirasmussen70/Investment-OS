Set-StrictMode -Version Latest

$script:JarvisAllowedEnvironmentNames = @(
    "INVESTMENT_OS_SNAPSHOT",
    "JARVIS_API_TOKEN",
    "JARVIS_AUDIT_BACKUP_COUNT",
    "JARVIS_AUDIT_LOG",
    "JARVIS_AUDIT_MAX_BYTES",
    "JARVIS_AUDIT_PERSISTENT",
    "JARVIS_BIND_HOST",
    "JARVIS_ENV",
    "JARVIS_PORT",
    "JARVIS_RATE_LIMIT_PER_MINUTE"
)

function Assert-JarvisWindows {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "This deployment package requires Windows."
    }
}

function Get-JarvisDefaultRuntimeRoot {
    $localAppData = [Environment]::GetFolderPath(
        [Environment+SpecialFolder]::LocalApplicationData
    )
    if ([string]::IsNullOrWhiteSpace($localAppData)) {
        throw "LocalAppData could not be resolved."
    }
    return Join-Path $localAppData "InvestmentOS\Jarvis"
}

function Import-JarvisEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Jarvis configuration file does not exist."
    }

    $loaded = @{}
    foreach ($line in Get-Content -LiteralPath $ConfigPath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $separator = $trimmed.IndexOf("=")
        if ($separator -lt 1) {
            throw "Jarvis configuration contains an invalid line."
        }

        $name = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()
        if ($script:JarvisAllowedEnvironmentNames -notcontains $name) {
            throw "Jarvis configuration contains an unsupported setting: $name"
        }
        if ($loaded.ContainsKey($name)) {
            throw "Jarvis configuration contains a duplicate setting: $name"
        }

        [Environment]::SetEnvironmentVariable($name, $value, "Process")
        $loaded[$name] = $value
    }
    return $loaded
}

function Assert-JarvisEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Settings
    )

    $required = @(
        "INVESTMENT_OS_SNAPSHOT",
        "JARVIS_API_TOKEN",
        "JARVIS_AUDIT_BACKUP_COUNT",
        "JARVIS_AUDIT_LOG",
        "JARVIS_AUDIT_MAX_BYTES",
        "JARVIS_AUDIT_PERSISTENT",
        "JARVIS_BIND_HOST",
        "JARVIS_ENV",
        "JARVIS_PORT",
        "JARVIS_RATE_LIMIT_PER_MINUTE"
    )
    foreach ($name in $required) {
        if (-not $Settings.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($Settings[$name])) {
            throw "Jarvis configuration is missing a required setting: $name"
        }
    }

    if ($Settings["JARVIS_ENV"] -ne "production") {
        throw "Windows deployment requires JARVIS_ENV=production."
    }
    if ($Settings["JARVIS_BIND_HOST"] -ne "127.0.0.1") {
        throw "Local-first deployment only permits JARVIS_BIND_HOST=127.0.0.1."
    }
    if ($Settings["JARVIS_AUDIT_PERSISTENT"].ToLowerInvariant() -ne "true") {
        throw "Windows deployment requires persistent audit storage."
    }
    if ($Settings["JARVIS_API_TOKEN"].Length -lt 32) {
        throw "JARVIS_API_TOKEN must contain at least 32 characters."
    }
    if (-not [IO.Path]::IsPathRooted($Settings["JARVIS_AUDIT_LOG"])) {
        throw "JARVIS_AUDIT_LOG must be an absolute path."
    }
    if (-not [IO.Path]::IsPathRooted($Settings["INVESTMENT_OS_SNAPSHOT"])) {
        throw "INVESTMENT_OS_SNAPSHOT must be an absolute path."
    }

    $positiveIntegers = @(
        "JARVIS_AUDIT_BACKUP_COUNT",
        "JARVIS_AUDIT_MAX_BYTES",
        "JARVIS_PORT",
        "JARVIS_RATE_LIMIT_PER_MINUTE"
    )
    foreach ($name in $positiveIntegers) {
        $parsed = 0
        if (-not [int]::TryParse($Settings[$name], [ref]$parsed) -or $parsed -le 0) {
            throw "$name must be a positive integer."
        }
        if ($name -eq "JARVIS_PORT" -and $parsed -gt 65535) {
            throw "JARVIS_PORT must not exceed 65535."
        }
        if ($name -eq "JARVIS_AUDIT_BACKUP_COUNT" -and $parsed -gt 100) {
            throw "JARVIS_AUDIT_BACKUP_COUNT must not exceed 100."
        }
    }

    if (-not (Test-Path -LiteralPath $Settings["INVESTMENT_OS_SNAPSHOT"] -PathType Leaf)) {
        throw "The configured Investment OS snapshot does not exist."
    }
}

function Get-JarvisPythonPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepositoryPath
    )

    $pythonPath = Join-Path $RepositoryPath ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Jarvis virtual environment is missing. Run Install-Jarvis.ps1 first."
    }
    return $pythonPath
}

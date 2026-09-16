[CmdletBinding()]
param(
    [string]$TaskName = "InvestmentOS-Jarvis"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "Jarvis.Windows.ps1")

Assert-JarvisWindows
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Jarvis scheduled task is not installed."
    exit 0
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Jarvis scheduled task was removed. Configuration and audit data were preserved."

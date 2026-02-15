<#
.SYNOPSIS
    Force stops NordVPN and disables common auto-start paths.
.DESCRIPTION
    Stops Nord-related processes, services, and scheduled tasks.
    Removes Nord-related startup entries from Run keys and Startup folders.
#>

$ErrorActionPreference = 'SilentlyContinue'

$nordRegex = '(?i)nord|nordvpn|nordsec'
$killedProcesses = 0
$stoppedServices = 0
$disabledServices = 0
$disabledTasks = 0
$removedRunEntries = 0
$removedStartupItems = 0

$processes = Get-Process | Where-Object {
    $_.Name -match $nordRegex -or $_.Path -match $nordRegex
}

foreach ($proc in $processes) {
    if (-not $proc.HasExited) {
        Write-Host "Killing process $($proc.Name) (PID: $($proc.Id))"
        Stop-Process -Id $proc.Id -Force
        $killedProcesses++
    }
}

$services = Get-Service | Where-Object {
    $_.Name -match $nordRegex -or $_.DisplayName -match $nordRegex
}

foreach ($svc in $services) {
    if ($svc.Status -ne 'Stopped') {
        Write-Host "Stopping service $($svc.Name)"
        Stop-Service -Name $svc.Name -Force
        $stoppedServices++
    }

    $serviceCim = Get-CimInstance Win32_Service -Filter "Name='$($svc.Name)'"
    if ($serviceCim.StartMode -ne 'Disabled') {
        Write-Host "Disabling service $($svc.Name)"
        Set-Service -Name $svc.Name -StartupType Disabled
        $disabledServices++
    }
}

$tasks = Get-ScheduledTask | Where-Object {
    $_.TaskName -match $nordRegex -or $_.TaskPath -match $nordRegex
}

foreach ($task in $tasks) {
    if ($task.State -ne 'Disabled') {
        Write-Host "Disabling scheduled task $($task.TaskPath)$($task.TaskName)"
        Disable-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath | Out-Null
        $disabledTasks++
    }
}

$runKeyPaths = @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce'
)

foreach ($keyPath in $runKeyPaths) {
    if (Test-Path $keyPath) {
        $props = Get-ItemProperty -Path $keyPath
        foreach ($prop in $props.PSObject.Properties) {
            if ($prop.Name -in 'PSPath', 'PSParentPath', 'PSChildName', 'PSDrive', 'PSProvider') {
                continue
            }

            $valueText = [string]$prop.Value
            if ($prop.Name -match $nordRegex -or $valueText -match $nordRegex) {
                Write-Host "Removing Run entry '$($prop.Name)' from $keyPath"
                Remove-ItemProperty -Path $keyPath -Name $prop.Name -Force
                $removedRunEntries++
            }
        }
    }
}

$startupDirs = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
)

foreach ($dir in $startupDirs) {
    if (Test-Path $dir) {
        $items = Get-ChildItem -Path $dir -Force
        foreach ($item in $items) {
            if ($item.Name -match $nordRegex -or $item.FullName -match $nordRegex) {
                Write-Host "Removing startup item $($item.FullName)"
                Remove-Item -Path $item.FullName -Force
                $removedStartupItems++
            }
        }
    }
}

$remainingProcesses = Get-Process | Where-Object {
    $_.Name -match $nordRegex -or $_.Path -match $nordRegex
}

Write-Host ""
Write-Host "Summary"
Write-Host "- Killed processes: $killedProcesses"
Write-Host "- Stopped services: $stoppedServices"
Write-Host "- Disabled services: $disabledServices"
Write-Host "- Disabled scheduled tasks: $disabledTasks"
Write-Host "- Removed Run entries: $removedRunEntries"
Write-Host "- Removed Startup items: $removedStartupItems"

if ($remainingProcesses.Count -gt 0) {
    Write-Host "- Warning: $($remainingProcesses.Count) Nord-related process(es) still running. Run this script as Administrator."
} else {
    Write-Host "- No Nord-related processes are running."
}

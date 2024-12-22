# Force Kill Processes by Exact Image Name

param (
    [Parameter(Mandatory = $true)]
    [string]$ImageName
)

# Retrieve processes by the exact image name
$processes = Get-Process | Where-Object { $_.Name -eq $ImageName }

if ($processes) {
    foreach ($process in $processes) {
        try {
            Stop-Process -Id $process.Id -Force -ErrorAction Stop
            Write-Output "Successfully terminated process: $($process.Name) (ID: $($process.Id))"
        } catch {
            Write-Output "Failed to terminate process: $($process.Name) (ID: $($process.Id)). Error: $($_.Exception.Message)"
        }
    }
} else {
    Write-Output "No processes found matching the image name: $ImageName"
}

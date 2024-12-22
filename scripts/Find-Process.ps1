# Find Processes by Partial Image Name

param (
    [Parameter(Mandatory = $true)]
    [string]$SearchTerm
)

# Retrieve processes that match the search term partially (case-insensitive)
$processes = Get-Process | Where-Object { $_.Name -like "*$SearchTerm*" -or $_.Path -like "*$SearchTerm*" }

if ($processes) {
    foreach ($process in $processes) {
        Write-Output "Found process: $($process.Name) (ID: $($process.Id))"
    }
} else {
    Write-Output "No processes found matching the search term: $SearchTerm"
}

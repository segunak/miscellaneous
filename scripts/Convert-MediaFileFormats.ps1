param (
    [string]$desiredImageFormat = "jpg",
    [string]$desiredVideoFormat = "mp4"
)

Write-Output "=== Script started at $(Get-Date) ==="
Write-Output "Desired image format: $desiredImageFormat, Desired video format: $desiredVideoFormat"

$timestamp = (Get-Date -Format "yyyyMMdd-HHmmss")
$outputFolder = "Output-$timestamp"
New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
Write-Output "Created output folder: $outputFolder"

$heicFiles = Get-ChildItem -Filter "*.heic"
$movFiles = Get-ChildItem -Filter "*.mov"
Write-Output "Found $($heicFiles.Count) HEIC files and $($movFiles.Count) MOV files."

if ($heicFiles.Count -eq 0 -and $movFiles.Count -eq 0) {
    Write-Output "No HEIC or MOV files found in the current directory. Exiting script."
    exit
}

Add-Type -AssemblyName System.Drawing
foreach ($file in $heicFiles) {
    $outputFile = Join-Path -Path $outputFolder -ChildPath ($file.BaseName + "." + $desiredImageFormat)
    Write-Output "Converting $($file.Name) to $desiredImageFormat..."
    try {
        $heicImage = [System.Drawing.Image]::FromFile($file.FullName)
        $heicImage.Save($outputFile, [System.Drawing.Imaging.ImageFormat]::Jpeg)
        $heicImage.Dispose()
        Write-Output "Successfully converted $($file.Name) to $outputFile"
    }
    catch {
        Write-Output "Error converting $($file.Name): $_"
    }
}

Write-Output "Starting MOV to $desiredVideoFormat conversion..."
foreach ($file in $movFiles) {
    $outputFile = Join-Path -Path $outputFolder -ChildPath ($file.BaseName + "." + $desiredVideoFormat)
    Write-Output "Converting $($file.Name) to $desiredVideoFormat..."
    try {
        & ffmpeg -i "$($file.FullName)" "$outputFile" -y
        Write-Output "Successfully converted $($file.Name) to $outputFile"
    }
    catch {
        Write-Output "Error converting $($file.Name): $_"
    }
}

Write-Output "=== Script completed at $(Get-Date) ==="

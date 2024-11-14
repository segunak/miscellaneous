# This script assumes ffmpeg is installed on your PATH.

param (
    [string]$desiredImageFormat = "jpg",
    [string]$desiredVideoFormat = "mp4"
)

$timestamp = (Get-Date -Format "yyyyMMdd-HHmmss")
$outputFolder = "Output-$timestamp"
New-Item -ItemType Directory -Path $outputFolder

$heicFiles = Get-ChildItem -Filter "*.heic"
$movFiles = Get-ChildItem -Filter "*.mov"

if ($heicFiles.Count -eq 0 -and $movFiles.Count -eq 0) {
    Write-Host "No HEIC or MOV files found in the current directory."
    exit
}

foreach ($file in $heicFiles) {
    $outputFile = Join-Path -Path $outputFolder -ChildPath ($file.BaseName + "." + $desiredImageFormat)

    # Perform the conversion using Windows.Graphics.Imaging
    try {
        $stream = [Windows.Storage.Streams.RandomAccessStreamReference]::CreateFromFile($file.FullName).OpenReadAsync().AsTask().Result
        $decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream).AsTask().Result
        $pixelData = $decoder.GetPixelDataAsync().AsTask().Result.DetachPixelData()

        $encoderStream = [Windows.Storage.Streams.RandomAccessStreamReference]::CreateFromFile($outputFile).OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite).AsTask().Result
        $encoder = [Windows.Graphics.Imaging.BitmapEncoder]::CreateAsync([Windows.Graphics.Imaging.BitmapEncoder]::JpegEncoderId, $encoderStream).AsTask().Result

        $encoder.SetPixelData($decoder.BitmapPixelFormat, $decoder.BitmapAlphaMode, $decoder.PixelWidth, $decoder.PixelHeight, $decoder.DpiX, $decoder.DpiY, $pixelData)
        $encoder.FlushAsync().AsTask().Wait()

        Write-Host "Converted $($file.Name) to $desiredImageFormat and saved to $outputFile"
    }
    catch {
        Write-Host "Failed to convert $($file.Name): $($_.Exception.Message)"
    }
}

foreach ($file in $movFiles) {
    $outputFile = Join-Path -Path $outputFolder -ChildPath ($file.BaseName + "." + $desiredVideoFormat)
    
    try {
        # Use ffmpeg to convert .mov to the desired video format
        $ffmpegCommand = "ffmpeg -i `"$($file.FullName)`" -qscale 0 `"$outputFile`""
        Invoke-Expression $ffmpegCommand

        Write-Host "Converted $($file.Name) to $desiredVideoFormat and saved to $outputFile"
    }
    catch {
        Write-Host "Failed to convert $($file.Name): $($_.Exception.Message)"
    }
}

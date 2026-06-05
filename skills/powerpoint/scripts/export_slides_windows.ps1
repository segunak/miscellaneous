param(
    [Parameter(Mandatory = $true)]
    [string]$PptxPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [int]$Width = 1920,
    [int]$Height = 1080
)

$ErrorActionPreference = "Stop"
$resolvedPptx = (Resolve-Path -LiteralPath $PptxPath).Path
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$resolvedOutput = (Resolve-Path -LiteralPath $OutputDir).Path

$powerPoint = $null
$presentation = $null

try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerPoint.Presentations.Open($resolvedPptx, $false, $false, $false)

    for ($index = 1; $index -le $presentation.Slides.Count; $index++) {
        $fileName = "slide-{0:D2}.png" -f $index
        $target = Join-Path $resolvedOutput $fileName
        $presentation.Slides.Item($index).Export($target, "PNG", $Width, $Height)
    }

    [pscustomobject]@{
        ok = $true
        slides = $presentation.Slides.Count
        outputDir = $resolvedOutput
    } | ConvertTo-Json
}
finally {
    if ($presentation -ne $null) {
        $presentation.Close()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    }
    if ($powerPoint -ne $null) {
        $powerPoint.Quit()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) | Out-Null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
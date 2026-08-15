[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop
Add-Type -AssemblyName System.Drawing

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$extensionRoot = Split-Path -Parent $scriptRoot
$sourceIconPath = Join-Path $extensionRoot "public\icons\plwc-icon-512.png"
$outputRoot = Join-Path $extensionRoot "store\assets"

if (-not (Test-Path -LiteralPath $sourceIconPath -PathType Leaf)) {
    throw "The canonical PLwC Store icon is missing: $sourceIconPath"
}

[IO.Directory]::CreateDirectory($outputRoot) | Out-Null

function Set-HighQualityRendering {
    param([Parameter(Mandatory = $true)][Drawing.Graphics] $Graphics)

    $Graphics.CompositingMode = [Drawing.Drawing2D.CompositingMode]::SourceOver
    $Graphics.CompositingQuality = [Drawing.Drawing2D.CompositingQuality]::HighQuality
    $Graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $Graphics.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $Graphics.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::HighQuality
    $Graphics.TextRenderingHint = [Drawing.Text.TextRenderingHint]::ClearTypeGridFit
}

function Write-ResizedIcon {
    param(
        [Parameter(Mandatory = $true)][Drawing.Image] $Source,
        [Parameter(Mandatory = $true)][int] $Size,
        [Parameter(Mandatory = $true)][string] $Path
    )

    $bitmap = [Drawing.Bitmap]::new(
        $Size,
        $Size,
        [Drawing.Imaging.PixelFormat]::Format32bppArgb
    )
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        Set-HighQualityRendering -Graphics $graphics
        $graphics.Clear([Drawing.Color]::Transparent)
        $graphics.DrawImage($Source, 0, 0, $Size, $Size)
        $bitmap.Save($Path, [Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

function Write-SmallPromoTile {
    param(
        [Parameter(Mandatory = $true)][Drawing.Image] $Source,
        [Parameter(Mandatory = $true)][string] $Path
    )

    $bitmap = [Drawing.Bitmap]::new(
        440,
        280,
        [Drawing.Imaging.PixelFormat]::Format32bppArgb
    )
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    $background = [Drawing.Drawing2D.LinearGradientBrush]::new(
        [Drawing.Rectangle]::new(0, 0, 440, 280),
        [Drawing.ColorTranslator]::FromHtml("#071321"),
        [Drawing.ColorTranslator]::FromHtml("#103650"),
        18.0
    )
    $accent = [Drawing.SolidBrush]::new(
        [Drawing.ColorTranslator]::FromHtml("#24D7D0")
    )
    $primary = [Drawing.SolidBrush]::new([Drawing.Color]::White)
    $secondary = [Drawing.SolidBrush]::new(
        [Drawing.ColorTranslator]::FromHtml("#C7EAF2")
    )
    $titleFont = [Drawing.Font]::new(
        "Segoe UI",
        27,
        [Drawing.FontStyle]::Bold,
        [Drawing.GraphicsUnit]::Pixel
    )
    $subtitleFont = [Drawing.Font]::new(
        "Segoe UI",
        16,
        [Drawing.FontStyle]::Regular,
        [Drawing.GraphicsUnit]::Pixel
    )
    try {
        Set-HighQualityRendering -Graphics $graphics
        $graphics.FillRectangle($background, 0, 0, 440, 280)
        $graphics.FillRectangle($accent, 204, 52, 4, 176)
        $graphics.DrawImage($Source, 28, 56, 168, 168)
        $graphics.DrawString(
            "PLwC`nChat Bridge",
            $titleFont,
            $primary,
            [Drawing.RectangleF]::new(230, 52, 190, 78)
        )
        $graphics.DrawString(
            "Local governance bridge for ChatGPT",
            $subtitleFont,
            $secondary,
            [Drawing.RectangleF]::new(230, 150, 184, 72)
        )
        $bitmap.Save($Path, [Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $subtitleFont.Dispose()
        $titleFont.Dispose()
        $secondary.Dispose()
        $primary.Dispose()
        $accent.Dispose()
        $background.Dispose()
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

$sourceIcon = [Drawing.Image]::FromFile($sourceIconPath)
try {
    Write-ResizedIcon `
        -Source $sourceIcon `
        -Size 128 `
        -Path (Join-Path $outputRoot "plwc-chat-bridge-icon-128.png")
    Write-ResizedIcon `
        -Source $sourceIcon `
        -Size 300 `
        -Path (Join-Path $outputRoot "plwc-chat-bridge-edge-logo-300.png")
    Write-SmallPromoTile `
        -Source $sourceIcon `
        -Path (Join-Path $outputRoot "plwc-chat-bridge-small-promo-440x280.png")
}
finally {
    $sourceIcon.Dispose()
}

Get-ChildItem -LiteralPath $outputRoot -File -Filter "*.png" |
    Sort-Object Name |
    ForEach-Object {
    [PSCustomObject]@{
        Name = $_.Name
        Bytes = $_.Length
        Sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).
            Hash.ToLowerInvariant()
    }
}

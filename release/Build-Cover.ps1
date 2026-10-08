param(
    [string] $OutputPath = (Join-Path $PSScriptRoot 'OpenMCM-1.0.0-cover.png')
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

# Original typography and line geometry. No game assets or third-party logos.
$bitmap = [System.Drawing.Bitmap]::new(1920, 1080)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
$resources = [System.Collections.Generic.List[System.IDisposable]]::new()

function New-Brush([string] $Hex) {
    $brush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml($Hex))
    $resources.Add($brush)
    return $brush
}

function New-Pen([string] $Hex, [single] $Width) {
    $pen = [System.Drawing.Pen]::new([System.Drawing.ColorTranslator]::FromHtml($Hex), $Width)
    $resources.Add($pen)
    return $pen
}

function New-Font([single] $Size, [System.Drawing.FontStyle] $Style = [System.Drawing.FontStyle]::Regular) {
    $font = [System.Drawing.Font]::new('Segoe UI', $Size, $Style, [System.Drawing.GraphicsUnit]::Pixel)
    $resources.Add($font)
    return $font
}

function Draw-CenteredText([string] $Text, [System.Drawing.Font] $Font,
    [System.Drawing.Brush] $Brush, [single] $Y, [single] $Height) {
    $format = [System.Drawing.StringFormat]::new()
    try {
        $format.Alignment = [System.Drawing.StringAlignment]::Center
        $format.LineAlignment = [System.Drawing.StringAlignment]::Center
        $format.FormatFlags = [System.Drawing.StringFormatFlags]::NoWrap
        $graphics.DrawString($Text, $Font, $Brush,
            [System.Drawing.RectangleF]::new(120, $Y, 1680, $Height), $format)
    }
    finally { $format.Dispose() }
}

try {
    $graphics.Clear([System.Drawing.ColorTranslator]::FromHtml('#171A1D'))
    $background = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
        [System.Drawing.Rectangle]::new(0, 0, 1920, 1080),
        [System.Drawing.ColorTranslator]::FromHtml('#23272B'),
        [System.Drawing.ColorTranslator]::FromHtml('#111416'), 90)
    $resources.Add($background)
    $graphics.FillRectangle($background, 0, 0, 1920, 1080)

    $white = New-Brush '#F0EEE8'
    $muted = New-Brush '#B6B9BA'
    $gold = New-Brush '#C4B28A'
    $border = New-Pen '#626361' 1.5
    $goldLine = New-Pen '#C4B28A' 2
    $dimLine = New-Pen '#515550' 1

    $graphics.DrawRectangle($border, 72, 72, 1776, 936)
    # Discrete corner bars keep the frame flat and distinctly original.
    foreach ($corner in @(@(72,72,1,1), @(1848,72,-1,1), @(72,1008,1,-1), @(1848,1008,-1,-1))) {
        $x, $y, $dx, $dy = $corner
        $graphics.DrawLine($goldLine, $x, $y, ($x + 86 * $dx), $y)
        $graphics.DrawLine($goldLine, $x, $y, $x, ($y + 42 * $dy))
    }

    Draw-CenteredText 'SKYRIM SE / AE' (New-Font 28) $gold 153 44
    $graphics.DrawLine($dimLine, 296, 260, 850, 260)
    $graphics.DrawLine($dimLine, 1070, 260, 1624, 260)
    Draw-CenteredText '1.0.0' (New-Font 29) $muted 237 44

    Draw-CenteredText 'OpenMCM' (New-Font 170 ([System.Drawing.FontStyle]::Bold)) $white 365 218
    Draw-CenteredText 'STANDALONE MOD CONFIGURATION MENU' (New-Font 35) $muted 604 56

    $graphics.DrawLine($goldLine, 875, 728, 1045, 728)
    Draw-CenteredText 'SKSE REQUIRED' (New-Font 27) $gold 864 44
    $graphics.DrawLine($dimLine, 620, 886, 802, 886)
    $graphics.DrawLine($dimLine, 1118, 886, 1300, 886)

    $bitmap.Save([IO.Path]::GetFullPath($OutputPath), [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output ([IO.Path]::GetFullPath($OutputPath))
}
finally {
    foreach ($resource in $resources) { $resource.Dispose() }
    $graphics.Dispose()
    $bitmap.Dispose()
}

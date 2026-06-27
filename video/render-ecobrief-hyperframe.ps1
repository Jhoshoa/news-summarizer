Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

$OutputPath = Join-Path $PSScriptRoot "ecobrief-hyperframe-demo.avi"
$Width = 640
$Height = 360
$Fps = 10
$DurationSeconds = 30
$FrameCount = $Fps * $DurationSeconds
$FrameStride = (($Width * 3 + 3) -band -bnot 3)
$FrameBytes = $FrameStride * $Height

function Write-FourCc($Writer, [string]$Value) {
    $bytes = [Text.Encoding]::ASCII.GetBytes($Value)
    $Writer.Write($bytes)
}

function Begin-Chunk($Writer, [string]$Id) {
    Write-FourCc $Writer $Id
    $pos = $Writer.BaseStream.Position
    $Writer.Write([UInt32]0)
    return $pos
}

function End-Chunk($Writer, [Int64]$SizePosition) {
    $end = $Writer.BaseStream.Position
    $size = [UInt32]($end - $SizePosition - 4)
    $Writer.BaseStream.Seek($SizePosition, [IO.SeekOrigin]::Begin) | Out-Null
    $Writer.Write($size)
    $Writer.BaseStream.Seek($end, [IO.SeekOrigin]::Begin) | Out-Null
    if (($size % 2) -eq 1) {
        $Writer.Write([byte]0)
    }
}

function Begin-List($Writer, [string]$Type) {
    Write-FourCc $Writer "LIST"
    $pos = $Writer.BaseStream.Position
    $Writer.Write([UInt32]0)
    Write-FourCc $Writer $Type
    return $pos
}

function Draw-RoundedRect($G, [float]$X, [float]$Y, [float]$W, [float]$H, [float]$R, $Brush, $Pen = $null) {
    $path = New-Object Drawing.Drawing2D.GraphicsPath
    $d = $R * 2
    $path.AddArc($X, $Y, $d, $d, 180, 90)
    $path.AddArc($X + $W - $d, $Y, $d, $d, 270, 90)
    $path.AddArc($X + $W - $d, $Y + $H - $d, $d, $d, 0, 90)
    $path.AddArc($X, $Y + $H - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    if ($Brush) { $G.FillPath($Brush, $path) }
    if ($Pen) { $G.DrawPath($Pen, $path) }
    $path.Dispose()
}

function Draw-Text($G, [string]$Text, [float]$X, [float]$Y, [float]$W, [float]$H, $Font, $Brush, [string]$Align = "Near") {
    $fmt = New-Object Drawing.StringFormat
    $fmt.Alignment = [Drawing.StringAlignment]::$Align
    $fmt.LineAlignment = [Drawing.StringAlignment]::Near
    $fmt.Trimming = [Drawing.StringTrimming]::EllipsisWord
    $G.DrawString($Text, $Font, $Brush, (New-Object Drawing.RectangleF($X, $Y, $W, $H)), $fmt)
    $fmt.Dispose()
}

function Ease([double]$T) {
    if ($T -lt 0) { return 0 }
    if ($T -gt 1) { return 1 }
    return $T * $T * (3 - 2 * $T)
}

function Lerp([double]$A, [double]$B, [double]$T) {
    return $A + (($B - $A) * (Ease $T))
}

function New-Brush([int]$R, [int]$G, [int]$B, [int]$A = 255) {
    return New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb($A, $R, $G, $B))
}

function New-Pen([int]$R, [int]$G, [int]$B, [float]$W = 1, [int]$A = 255) {
    return New-Object Drawing.Pen ([Drawing.Color]::FromArgb($A, $R, $G, $B)), $W
}

$fontTitle = New-Object Drawing.Font("Segoe UI Semibold", 30, [Drawing.FontStyle]::Bold, [Drawing.GraphicsUnit]::Pixel)
$fontH1 = New-Object Drawing.Font("Segoe UI Semibold", 24, [Drawing.FontStyle]::Bold, [Drawing.GraphicsUnit]::Pixel)
$fontH2 = New-Object Drawing.Font("Segoe UI Semibold", 18, [Drawing.FontStyle]::Bold, [Drawing.GraphicsUnit]::Pixel)
$fontBody = New-Object Drawing.Font("Segoe UI", 14, [Drawing.FontStyle]::Regular, [Drawing.GraphicsUnit]::Pixel)
$fontSmall = New-Object Drawing.Font("Segoe UI", 11, [Drawing.FontStyle]::Regular, [Drawing.GraphicsUnit]::Pixel)
$fontMetric = New-Object Drawing.Font("Segoe UI Semibold", 28, [Drawing.FontStyle]::Bold, [Drawing.GraphicsUnit]::Pixel)

$white = New-Brush 245 249 246
$muted = New-Brush 181 194 190
$green = New-Brush 65 203 141
$lime = New-Brush 188 234 93
$ink = New-Brush 17 29 34
$panel = New-Brush 21 35 40 235
$panel2 = New-Brush 31 50 55 235
$linePen = New-Pen 82 115 112 1.3 180
$greenPen = New-Pen 65 203 141 2.2
$limePen = New-Pen 188 234 93 2.0

function Draw-Base($G, [double]$Seconds) {
    $G.Clear([Drawing.Color]::FromArgb(9, 17, 20))
    $bg1 = New-Object Drawing.Drawing2D.LinearGradientBrush(
        (New-Object Drawing.Rectangle(0, 0, $Width, $Height)),
        [Drawing.Color]::FromArgb(11, 23, 27),
        [Drawing.Color]::FromArgb(28, 47, 45),
        35
    )
    $G.FillRectangle($bg1, 0, 0, $Width, $Height)
    $bg1.Dispose()
    for ($i = 0; $i -lt 42; $i++) {
        $x = (($i * 53 + [int]($Seconds * 18)) % ($Width + 80)) - 40
        $y = (($i * 29 + 37) % ($Height + 40)) - 20
        $alpha = 25 + (($i * 7) % 40)
        $dot = New-Brush 111 167 151 $alpha
        $G.FillEllipse($dot, $x, $y, 2, 2)
        $dot.Dispose()
    }
    $G.DrawLine($linePen, 0, 316, $Width, 316)
}

function Draw-Pill($G, [string]$Text, [float]$X, [float]$Y, [float]$W) {
    Draw-RoundedRect $G $X $Y $W 28 8 (New-Brush 65 203 141 36) $greenPen
    Draw-Text $G $Text ($X + 12) ($Y + 6) ($W - 24) 18 $fontSmall $white
}

function Draw-Header($G, [string]$Label) {
    Draw-Text $G "EcoBrief Bolivia" 24 18 190 22 $fontH2 $white
    Draw-Text $G $Label 430 22 184 20 $fontSmall $muted "Far"
}

function Draw-FlowNode($G, [string]$Label, [float]$X, [float]$Y, [bool]$Active) {
    $brush = if ($Active) { New-Brush 65 203 141 58 } else { $panel2 }
    $pen = if ($Active) { $greenPen } else { $linePen }
    Draw-RoundedRect $G $X $Y 84 50 7 $brush $pen
    Draw-Text $G $Label ($X + 8) ($Y + 13) 68 28 $fontSmall $white "Center"
}

function Draw-AppPanel($G, [double]$T) {
    Draw-RoundedRect $G 48 76 544 214 10 $panel $linePen
    Draw-RoundedRect $G 70 101 170 166 8 (New-Brush 11 22 26) $greenPen
    Draw-Text $G "Brief movil" 88 118 120 18 $fontSmall $muted
    Draw-Text $G "Menos ruido.`nMas claridad local." 88 142 126 54 $fontH2 $white
    Draw-RoundedRect $G 88 212 120 12 4 (New-Brush 65 203 141 145)
    Draw-RoundedRect $G 88 233 88 12 4 (New-Brush 188 234 93 145)
    $tabs = @("Home", "Noticias", "Detalle", "Impacto", "Suscripcion")
    for ($i = 0; $i -lt $tabs.Count; $i++) {
        $active = [int]([Math]::Min(4, [Math]::Floor($T * 5))) -eq $i
        $x = 270 + (($i % 3) * 94)
        $y = 108 + ([Math]::Floor($i / 3) * 72)
        $b = if ($active) { New-Brush 65 203 141 56 } else { New-Brush 32 51 56 }
        $p = if ($active) { $greenPen } else { $linePen }
        Draw-RoundedRect $G $x $y 78 48 7 $b $p
        Draw-Text $G $tabs[$i] ($x + 6) ($y + 16) 66 18 $fontSmall $white "Center"
        $b.Dispose()
    }
    Draw-Text $G "MVP funcional: frontend, API, BD, IA y metricas" 270 238 270 22 $fontBody $white
}

function Draw-ImpactBars($G, [double]$T) {
    $metrics = @(
        @("Paginas evitadas", "42", 0.88),
        @("Llamadas IA evitadas", "18", 0.62),
        @("MB no descargados", "34", 0.74),
        @("Reduccion flujo", "71%", 0.71)
    )
    for ($i = 0; $i -lt $metrics.Count; $i++) {
        $x = 70 + (($i % 2) * 250)
        $y = 104 + ([Math]::Floor($i / 2) * 92)
        Draw-RoundedRect $G $x $y 206 66 8 $panel $linePen
        Draw-Text $G $metrics[$i][1] ($x + 18) ($y + 10) 72 34 $fontMetric $green
        Draw-Text $G $metrics[$i][0] ($x + 92) ($y + 16) 94 24 $fontSmall $white
        Draw-RoundedRect $G ($x + 18) ($y + 48) 168 7 3 (New-Brush 59 76 75)
        Draw-RoundedRect $G ($x + 18) ($y + 48) ([float](168 * $metrics[$i][2] * (Ease $T))) 7 3 $lime
    }
}

function Draw-Frame($Bitmap, [int]$FrameNumber) {
    $seconds = $FrameNumber / $Fps
    $G = [Drawing.Graphics]::FromImage($Bitmap)
    $G.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $G.TextRenderingHint = [Drawing.Text.TextRenderingHint]::ClearTypeGridFit
    Draw-Base $G $seconds

    if ($seconds -lt 4) {
        $t = $seconds / 4
        Draw-Header $G "Concept demo | Green Tech 2026"
        Draw-Pill $G "IA responsable + menor desperdicio digital" 175 90 290
        Draw-Text $G "EcoBrief`nBolivia" 70 ([float](132 + (16 * (1 - (Ease $t))))) 500 82 $fontTitle $white "Center"
        Draw-Text $G "Usamos IA para reducir ruido, duplicacion, datos innecesarios y tiempo perdido al informarse." 98 232 444 46 $fontBody $muted "Center"
    } elseif ($seconds -lt 8) {
        $t = ($seconds - 4) / 4
        Draw-Header $G "Problema"
        Draw-Text $G "Informarse consume mas recursos de los necesarios" 48 70 520 34 $fontH1 $white
        $items = @("Muchos sitios abiertos", "Noticias repetidas", "Scroll social sin trazabilidad", "IA procesando contenido duplicado")
        for ($i = 0; $i -lt 4; $i++) {
            $x = 54 + (($i % 2) * 270)
            $y = 128 + ([Math]::Floor($i / 2) * 78)
            $visible = (Ease ([Math]::Min(1, [Math]::Max(0, ($t * 4) - $i)))) 
            Draw-RoundedRect $G $x ([float]($y + 18 * (1 - $visible))) 230 54 8 $panel2 $linePen
            Draw-Text $G $items[$i] ($x + 16) ([float]($y + 16 + 18 * (1 - $visible))) 198 24 $fontBody $white "Center"
        }
    } elseif ($seconds -lt 13) {
        $t = ($seconds - 8) / 5
        Draw-Header $G "Flujo de solucion"
        Draw-Text $G "Primero reducimos. Luego usamos IA." 72 70 496 30 $fontH1 $white "Center"
        $nodes = @("Recolecta", "Limpia", "Deduplica", "Rankea", "Resume IA", "Publica")
        for ($i = 0; $i -lt $nodes.Count; $i++) {
            $x = 42 + ($i * 98)
            $active = ($t * 6) -ge $i
            Draw-FlowNode $G $nodes[$i] $x 158 $active
            if ($i -lt ($nodes.Count - 1)) {
                $pen = if (($t * 6) -gt ($i + 0.4)) { $greenPen } else { $linePen }
                $G.DrawLine($pen, ($x + 84), 183, ($x + 98), 183)
            }
        }
        Draw-Text $G "Menos paginas, menos tokens, briefs con fuente visible." 100 244 440 26 $fontBody $muted "Center"
    } elseif ($seconds -lt 18) {
        $t = ($seconds - 13) / 5
        Draw-Header $G "Mockup interactivo + prototipo funcional"
        Draw-AppPanel $G $t
    } elseif ($seconds -lt 23) {
        $t = ($seconds - 18) / 5
        Draw-Header $G "Dashboard de impacto"
        Draw-Text $G "Impacto medible con metricas transparentes" 62 64 516 30 $fontH1 $white "Center"
        Draw-ImpactBars $G $t
        Draw-Text $G "Estimaciones conservadoras basadas en reduccion operativa del flujo." 94 286 452 22 $fontSmall $muted "Center"
    } elseif ($seconds -lt 27) {
        $t = ($seconds - 23) / 4
        Draw-Header $G "Automatizacion y canales"
        Draw-Text $G "Cron-jobs + preferencias + distribucion" 80 70 480 32 $fontH1 $white "Center"
        $labels = @("Scheduler", "FastAPI", "PostgreSQL", "Web", "Email", "Telegram", "WhatsApp")
        for ($i = 0; $i -lt $labels.Count; $i++) {
            $angle = ($i / $labels.Count) * [Math]::PI * 2 + ($t * 0.5)
            $x = 320 + [Math]::Cos($angle) * 190
            $y = 188 + [Math]::Sin($angle) * 78
            Draw-RoundedRect $G ([float]($x - 48)) ([float]($y - 18)) 96 36 7 (New-Brush 31 50 55) $linePen
            Draw-Text $G $labels[$i] ([float]($x - 42)) ([float]($y - 7)) 84 14 $fontSmall $white "Center"
            $G.DrawLine($greenPen, 320, 188, [float]$x, [float]$y)
        }
        Draw-RoundedRect $G 265 160 110 56 8 (New-Brush 65 203 141 66) $greenPen
        Draw-Text $G "EcoBrief`nBriefs utiles" 275 172 90 32 $fontSmall $white "Center"
    } else {
        $t = ($seconds - 27) / 3
        Draw-Header $G "Cierre"
        Draw-Text $G "IA para reducir,`nno para multiplicar." 58 104 524 86 $fontTitle $white "Center"
        Draw-Text $G "EcoBrief Bolivia demuestra Green Tech con un MVP operativo, impacto visible y bajo costo." 82 224 476 42 $fontBody $muted "Center"
        Draw-RoundedRect $G 214 286 212 28 8 (New-Brush 65 203 141 ([int](45 + 80 * (Ease $t)))) $greenPen
        Draw-Text $G "Smarter AI, Greener Impact" 226 293 188 16 $fontSmall $white "Center"
    }

    $progress = $seconds / $DurationSeconds
    Draw-RoundedRect $G 24 333 592 5 2 (New-Brush 61 79 78)
    Draw-RoundedRect $G 24 333 ([float](592 * $progress)) 5 2 $green
    $G.Dispose()
}

function Get-FrameBytes($Bitmap) {
    $rect = New-Object Drawing.Rectangle(0, 0, $Width, $Height)
    $data = $Bitmap.LockBits($rect, [Drawing.Imaging.ImageLockMode]::ReadOnly, [Drawing.Imaging.PixelFormat]::Format24bppRgb)
    try {
        $sourceStride = [Math]::Abs($data.Stride)
        $source = New-Object byte[] ($sourceStride * $Height)
        [Runtime.InteropServices.Marshal]::Copy($data.Scan0, $source, 0, $source.Length)
        $dest = New-Object byte[] $FrameBytes
        for ($y = 0; $y -lt $Height; $y++) {
            $srcOffset = ($Height - 1 - $y) * $sourceStride
            $dstOffset = $y * $FrameStride
            [Array]::Copy($source, $srcOffset, $dest, $dstOffset, [Math]::Min($sourceStride, $FrameStride))
        }
        return $dest
    } finally {
        $Bitmap.UnlockBits($data)
    }
}

if (!(Test-Path $PSScriptRoot)) {
    New-Item -ItemType Directory -Path $PSScriptRoot | Out-Null
}
$fs = [IO.File]::Open($OutputPath, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None)
$writer = New-Object IO.BinaryWriter($fs)
$index = New-Object System.Collections.Generic.List[object]

try {
    Write-FourCc $writer "RIFF"
    $riffSizePos = $writer.BaseStream.Position
    $writer.Write([UInt32]0)
    Write-FourCc $writer "AVI "

    $hdrl = Begin-List $writer "hdrl"
    $avih = Begin-Chunk $writer "avih"
    $writer.Write([UInt32](1000000 / $Fps))
    $writer.Write([UInt32]($FrameBytes * $Fps))
    $writer.Write([UInt32]0)
    $writer.Write([UInt32]0x10)
    $writer.Write([UInt32]$FrameCount)
    $writer.Write([UInt32]0)
    $writer.Write([UInt32]1)
    $writer.Write([UInt32]$FrameBytes)
    $writer.Write([UInt32]$Width)
    $writer.Write([UInt32]$Height)
    1..4 | ForEach-Object { $writer.Write([UInt32]0) }
    End-Chunk $writer $avih

    $strl = Begin-List $writer "strl"
    $strh = Begin-Chunk $writer "strh"
    Write-FourCc $writer "vids"
    Write-FourCc $writer "DIB "
    $writer.Write([UInt32]0)
    $writer.Write([UInt16]0)
    $writer.Write([UInt16]0)
    $writer.Write([UInt32]0)
    $writer.Write([UInt32]1)
    $writer.Write([UInt32]$Fps)
    $writer.Write([UInt32]0)
    $writer.Write([UInt32]$FrameCount)
    $writer.Write([UInt32]$FrameBytes)
    $writer.Write([UInt32]::MaxValue)
    $writer.Write([UInt32]0)
    $writer.Write([Int16]0)
    $writer.Write([Int16]0)
    $writer.Write([Int16]$Width)
    $writer.Write([Int16]$Height)
    End-Chunk $writer $strh

    $strf = Begin-Chunk $writer "strf"
    $writer.Write([UInt32]40)
    $writer.Write([Int32]$Width)
    $writer.Write([Int32]$Height)
    $writer.Write([UInt16]1)
    $writer.Write([UInt16]24)
    $writer.Write([UInt32]0)
    $writer.Write([UInt32]$FrameBytes)
    $writer.Write([Int32]0)
    $writer.Write([Int32]0)
    $writer.Write([UInt32]0)
    $writer.Write([UInt32]0)
    End-Chunk $writer $strf
    End-Chunk $writer $strl
    End-Chunk $writer $hdrl

    $movi = Begin-List $writer "movi"
    $moviDataStart = $writer.BaseStream.Position
    $bitmap = New-Object Drawing.Bitmap($Width, $Height, [Drawing.Imaging.PixelFormat]::Format24bppRgb)
    try {
        for ($frame = 0; $frame -lt $FrameCount; $frame++) {
            Draw-Frame $bitmap $frame
            $bytes = Get-FrameBytes $bitmap
            $chunkStart = $writer.BaseStream.Position
            Write-FourCc $writer "00db"
            $writer.Write([UInt32]$FrameBytes)
            $writer.BaseStream.Write($bytes, 0, $bytes.Length)
            $index.Add([PSCustomObject]@{
                Offset = [UInt32]($chunkStart - $moviDataStart)
                Size = [UInt32]$FrameBytes
            })
            if (($frame % 30) -eq 0) {
                Write-Host "Rendered frame $frame / $FrameCount"
            }
        }
    } finally {
        $bitmap.Dispose()
    }
    End-Chunk $writer $movi

    $idx = Begin-Chunk $writer "idx1"
    foreach ($entry in $index) {
        Write-FourCc $writer "00db"
        $writer.Write([UInt32]0x10)
        $writer.Write([UInt32]$entry.Offset)
        $writer.Write([UInt32]$entry.Size)
    }
    End-Chunk $writer $idx

    $end = $writer.BaseStream.Position
    $writer.BaseStream.Seek($riffSizePos, [IO.SeekOrigin]::Begin) | Out-Null
    $writer.Write([UInt32]($end - 8))
    $writer.BaseStream.Seek($end, [IO.SeekOrigin]::Begin) | Out-Null
} finally {
    $writer.Dispose()
    $fs.Dispose()
    $fontTitle.Dispose()
    $fontH1.Dispose()
    $fontH2.Dispose()
    $fontBody.Dispose()
    $fontSmall.Dispose()
    $fontMetric.Dispose()
    $white.Dispose()
    $muted.Dispose()
    $green.Dispose()
    $lime.Dispose()
    $ink.Dispose()
    $panel.Dispose()
    $panel2.Dispose()
    $linePen.Dispose()
    $greenPen.Dispose()
    $limePen.Dispose()
}

Write-Host "Exported $OutputPath"

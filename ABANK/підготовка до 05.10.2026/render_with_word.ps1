$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'Клопотання про ознайомлення з відповіддю банку — 01.10.2026.docx'
$qa = Join-Path $PSScriptRoot 'qa'
New-Item -ItemType Directory -Path $qa -Force | Out-Null
$pdf = Join-Path $qa 'request-preview.pdf'
$word = $null
$document = $null
$isolated = $false
try {
    $word = New-Object -ComObject Word.Application
    if ($word.Documents.Count -ne 0) { throw 'Word instance contains existing documents; refusing to use it.' }
    $isolated = $true
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($source, $false, $true, $false)
    $document.ExportAsFixedFormat($pdf, 17)
    Write-Output $pdf
} finally {
    if ($null -ne $document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }
    if ($null -ne $word) {
        if ($isolated) { $word.Quit(0) }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    }
}

param([int]$Only = 0)
$ErrorActionPreference = 'Stop'
$files = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'packet_files.json') | ConvertFrom-Json
if ($Only -gt 0) { $files = @($files | Where-Object { $_.number -eq $Only }) }
$word = $null
$document = $null
$isolated = $false
try {
    $word = New-Object -ComObject Word.Application
    if ($word.Documents.Count -ne 0) { throw 'Word instance contains existing documents; refusing to use it.' }
    $isolated = $true
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    foreach ($file in $files) {
        $source = Join-Path $PSScriptRoot $file.docx
        $destination = [IO.Path]::ChangeExtension($source, '.pdf')
        $document = $word.Documents.Open($source, $false, $true, $false)
        $document.ExportAsFixedFormat($destination, 17)
        $document.Close(0)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)
        $document = $null
        Write-Output "Rendered $($file.number): $destination"
    }
} finally {
    if ($null -ne $document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }
    if ($null -ne $word) {
        if ($isolated) { $word.Quit(0) }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    }
}

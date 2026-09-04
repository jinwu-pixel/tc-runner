param(
    [Parameter(Mandatory = $true)]
    [string]$Request,
    [Parameter(Mandatory = $true)]
    [string]$Out
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Release-ComObject {
    param([object]$Object)
    if ($null -ne $Object -and [System.Runtime.InteropServices.Marshal]::IsComObject($Object)) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($Object)
    }
}

function Get-SanitizedComErrorCode {
    param([System.Exception]$Exception)
    $bytes = [System.BitConverter]::GetBytes([int]$Exception.HResult)
    $unsigned = [System.BitConverter]::ToUInt32($bytes, 0)
    return "EXCEL_COM_{0}" -f $unsigned.ToString("X8")
}

function Get-RepoRelativePosixPath {
    param([string]$SourcePath)
    $root = [System.IO.Path]::GetFullPath((Get-Location).Path).TrimEnd("\") + "\"
    $source = [System.IO.Path]::GetFullPath($SourcePath)
    if (-not $source.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw [System.UnauthorizedAccessException]::new("Source is outside the repository root")
    }
    return $source.Substring($root.Length).Replace("\", "/")
}

$decoded = Get-Content -LiteralPath $Request -Raw -Encoding UTF8 | ConvertFrom-Json
$requestItems = @($decoded)
$results = [System.Collections.Generic.List[object]]::new()
$excel = $null
$workbooks = $null
$snapshotRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("skt-workbook-snapshots-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $snapshotRoot | Out-Null

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AskToUpdateLinks = $false
    $excel.EnableEvents = $false
    $excel.AutomationSecurity = 3
    $workbooks = $excel.Workbooks

    foreach ($requestItem in $requestItems) {
        $documentId = [string]$requestItem.document_id
        $sourcePath = [string]$requestItem.source_path
        $expectedHash = ([string]$requestItem.expected_source_sha256).ToLowerInvariant()
        $relativePath = Get-RepoRelativePosixPath -SourcePath $sourcePath
        $actualHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()

        if ($actualHash -ne $expectedHash) {
            $results.Add([ordered]@{
                document_id = $documentId
                path = $relativePath
                source_sha256 = $expectedHash
                acquisition_status = "FAILED"
                error_code = "SOURCE_HASH_DRIFT"
                sheet_count = 0
                sheets = @()
            })
            continue
        }

        $workbook = $null
        $worksheets = $null
        $snapshotPath = $null
        try {
            $snapshotPath = Join-Path $snapshotRoot ([guid]::NewGuid().ToString("N") + ".xls")
            Copy-Item -LiteralPath $sourcePath -Destination $snapshotPath
            $snapshotHash = (Get-FileHash -LiteralPath $snapshotPath -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($snapshotHash -ne $expectedHash) {
                $results.Add([ordered]@{
                    document_id = $documentId
                    path = $relativePath
                    source_sha256 = $expectedHash
                    acquisition_status = "FAILED"
                    error_code = "SOURCE_HASH_DRIFT"
                    sheet_count = 0
                    sheets = @()
                })
                continue
            }
            $workbook = $workbooks.Open($snapshotPath, 0, $true, [Type]::Missing, [Type]::Missing, [Type]::Missing, $true)
            $worksheets = $workbook.Worksheets
            $sheets = [System.Collections.Generic.List[object]]::new()
            $sheetCount = [int]$worksheets.Count
            for ($sheetIndex = 1; $sheetIndex -le $sheetCount; $sheetIndex++) {
                $worksheet = $null
                $usedRange = $null
                $usedRows = $null
                $usedColumns = $null
                try {
                    $worksheet = $worksheets.Item($sheetIndex)
                    $usedRange = $worksheet.UsedRange
                    $usedRows = $usedRange.Rows
                    $usedColumns = $usedRange.Columns
                    $firstRow = [int]$usedRange.Row
                    $firstColumn = [int]$usedRange.Column
                    $lastRow = $firstRow + [int]$usedRows.Count - 1
                    $lastColumn = $firstColumn + [int]$usedColumns.Count - 1
                    $visibility = switch ([int]$worksheet.Visible) {
                        -1 { "VISIBLE"; break }
                        0 { "HIDDEN"; break }
                        2 { "VERY_HIDDEN"; break }
                        default { throw [System.Runtime.InteropServices.COMException]::new("Unknown worksheet visibility") }
                    }
                    $sheets.Add([ordered]@{
                        sheet_index = $sheetIndex
                        sheet_name = [string]$worksheet.Name
                        visibility = $visibility
                        used_range = [ordered]@{
                            first_row = $firstRow
                            last_row = $lastRow
                            first_column = $firstColumn
                            last_column = $lastColumn
                        }
                    })
                }
                finally {
                    Release-ComObject -Object $usedRows
                    Release-ComObject -Object $usedColumns
                    Release-ComObject -Object $usedRange
                    Release-ComObject -Object $worksheet
                }
            }
            $results.Add([ordered]@{
                document_id = $documentId
                path = $relativePath
                source_sha256 = $expectedHash
                acquisition_status = "READABLE"
                error_code = $null
                sheet_count = $sheetCount
                sheets = @($sheets)
            })
        }
        catch {
            $results.Add([ordered]@{
                document_id = $documentId
                path = $relativePath
                source_sha256 = $expectedHash
                acquisition_status = "FAILED"
                error_code = Get-SanitizedComErrorCode -Exception $_.Exception
                sheet_count = 0
                sheets = @()
            })
        }
        finally {
            try {
                if ($null -ne $workbook) {
                    $workbook.Close($false)
                }
            }
            catch {
            }
            finally {
                Release-ComObject -Object $worksheets
                Release-ComObject -Object $workbook
                if ($null -ne $snapshotPath -and (Test-Path -LiteralPath $snapshotPath)) {
                    Remove-Item -LiteralPath $snapshotPath -Force
                }
                [GC]::Collect()
                [GC]::WaitForPendingFinalizers()
            }
        }
    }
}
finally {
    try {
        if ($null -ne $excel) {
            $excel.Quit()
        }
    }
    catch {
    }
    finally {
        Release-ComObject -Object $workbooks
        Release-ComObject -Object $excel
        if (Test-Path -LiteralPath $snapshotRoot) {
            Remove-Item -LiteralPath $snapshotRoot -Recurse -Force
        }
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

$payload = [ordered]@{ workbooks = @($results) }
$json = $payload | ConvertTo-Json -Depth 8
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Out, $json + [Environment]::NewLine, $utf8NoBom)

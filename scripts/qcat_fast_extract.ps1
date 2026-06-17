<#
qcat_fast_extract.ps1 — fast, robust QCAT .qmdl parsing (filtered text + ISF cache)

MEASURED on BTS15068 diag_log_*.qmdl (155 MB / 1,311,322 packets), QCAT 6.30.121:
  qmdl OpenLog .................. 147-157 s   <-- the FLOOR (indexes ALL packets;
                                                 86% are 0x1FEB Extended Debug we don't need)
  SaveAsISF (6 codes, filtered) . 0.6 s -> 2.14 MB ISF (9,115 packets)
  ISF re-OpenLog ................ 0.2 s        <-- ~740x faster than qmdl open
  SaveAsText from ISF ........... 0.5 s
  ISF-path data == qmdl-path data (RSRP identical, verified)

=> SPEEDUP STRATEGY (why this script is shaped this way):
  1. filter-FIRST: PacketFilter.SetAll($false) then Set() only needed codes BEFORE
     SaveAsText. Default (all-on) dumped 0x1FEB/0x1FE8 -> 564 MB text. Filtered = KB.
  2. ISF cache: pay the ~150 s qmdl open ONCE, write a tiny filtered .isf, then every
     follow-up query re-opens in 0.2 s. Build the ISF with a BROAD code superset so you
     never need to touch the slow qmdl again for this capture.
  3. ONE COM activation, do everything: each New-Object launches QCAT.exe (out-of-process
     COM server). On the FIRST launch Windows may pop a modal "Windows feature: DirectPlay"
     install prompt that BLOCKS QCAT.exe from finishing startup -> New-Object fails with
     0x80080005 CO_E_SERVER_EXEC_FAILURE (~120 s timeout). Background/non-interactive sessions
     CANNOT answer that modal, so they always fail. Fix: dismiss the modal (Skip) or install
     DirectPlay once; RUN FOREGROUND. Then open once and run all extractions in the single
     session (avoids re-paying the QCAT launch + the modal risk).
     (Earlier hypothesis "DCOM cooldown" was WRONG — the real blocker is the DirectPlay modal.)

NOTES / CAVEATS:
  - Timestamps in QCAT text output are UTC. KST = UTC + 9 h.
  - SetTimeWindowAbsolute(epoch) appeared INEFFECTIVE for SaveAsText in this 6.30 build
    (output still spanned the whole log). Rely on the packet filter + post-filter the text
    by timestamp in your parser. (kept here as best-effort only.)
  - Run FOREGROUND. Background/detached sessions fail COM activation (0x80080005).

USAGE
  # First touch on a capture: build the reusable ISF cache AND extract LTE meas:
  .\qcat_fast_extract.ps1 -Qmdl <q.qmdl> -Isf <cache.isf> -MakeIsf `
        -Codes 0xB193,0xB15B -Out lte_meas.txt
  # Later queries on the SAME capture (sub-second): just point at the ISF:
  .\qcat_fast_extract.ps1 -Isf <cache.isf> -Codes 0xB0EC -Out emm.txt
#>
param(
  [string]$Qmdl,
  [string]$Isf,
  [Parameter(Mandatory)][string]$Out,
  [Parameter(Mandatory)][int[]]$Codes,
  [switch]$MakeIsf,
  # broad superset kept in the ISF cache (LTE meas/antenna, LTE NAS EMM, LTE RRC OTA, WCDMA)
  [int[]]$IsfCodes = @(0xB193,0xB15B,0xB0EC,0xB0C0,0xB0E2,0x7001,0x4179,0x713A)
)

function New-Qcat {
  # NOTE: use Write-Host (NOT Write-Output) inside — Write-Output would pollute the
  # function's return value so $q becomes a String[] instead of the COM object.
  for ($i=1; $i -le 2; $i++) {
    try { return (New-Object -ComObject "QCAT6.Application" -ErrorAction Stop) }
    catch {
      Write-Host ("  COM activation attempt $i failed: " + $_.Exception.Message)
      Start-Sleep -Seconds 3
    }
  }
  throw ("QCAT COM activation failed (0x80080005 CO_E_SERVER_EXEC_FAILURE). " +
         "ROOT CAUSE is usually a modal 'Windows feature: DirectPlay' install prompt that " +
         "blocks QCAT.exe launch on first run — dismiss it (Skip) or install DirectPlay once. " +
         "Background/non-interactive sessions cannot answer the modal: run FOREGROUND.")
}
function Apply-Filter($q,$codes){ $pf=$q.PacketFilter; $pf.SetAll($false); foreach($c in $codes){ $null=$pf.Set($c,$true) }; $pf.Commit() }

Get-Process QCAT -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$sw=[System.Diagnostics.Stopwatch]::StartNew()
$q = New-Qcat

$useIsf = $Isf -and (Test-Path $Isf) -and -not $MakeIsf
if ($useIsf) {
  $null=$q.OpenLog($Isf); Write-Output ("[open] ISF $Isf = "+[math]::Round($sw.Elapsed.TotalSeconds,1)+" s  packets="+$q.PacketCount)
} else {
  if (-not (Test-Path $Qmdl)) { throw "No ISF cache and -Qmdl missing/invalid." }
  $null=$q.OpenLog($Qmdl); Write-Output ("[open] qmdl (SLOW) = "+[math]::Round($sw.Elapsed.TotalSeconds,1)+" s  packets="+$q.PacketCount)
  if ($Isf -and $MakeIsf) {
    Apply-Filter $q $IsfCodes
    $t=$sw.Elapsed.TotalSeconds; $null=$q.SaveAsISF($Isf)
    Write-Output ("[isf ] SaveAsISF = "+[math]::Round($sw.Elapsed.TotalSeconds-$t,1)+" s  size="+[math]::Round((Get-Item $Isf).Length/1MB,2)+" MB  err="+$q.LastError)
    $null=$q.closeFile(); $t=$sw.Elapsed.TotalSeconds; $null=$q.OpenLog($Isf)
    Write-Output ("[open] ISF re-open = "+[math]::Round($sw.Elapsed.TotalSeconds-$t,1)+" s  packets="+$q.PacketCount)
  }
}

Apply-Filter $q $Codes
$t=$sw.Elapsed.TotalSeconds; $null=$q.SaveAsText($Out)
Write-Output ("[text] SaveAsText = "+[math]::Round($sw.Elapsed.TotalSeconds-$t,1)+" s  size="+(Get-Item $Out).Length+" B  err="+$q.LastError)
Write-Output ("TOTAL = "+[math]::Round($sw.Elapsed.TotalSeconds,1)+" s")
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($q) | Out-Null
[GC]::Collect()

# Self-check for scripts/provenance_controller.ps1.
#
# Every failure class that consumed a dispatch capsule during the
# RB-20260728-shellrc-p0p1 attempts is reproduced here as a static or
# rehearsal check, so a drifted controller fails before a capsule is issued.
#
# ASCII-only by contract (Windows PowerShell 5.1 reads a BOM-less .ps1 as
# ANSI). Exit 0 = GREEN, exit 1 = at least one check FAILED.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$Failures = New-Object System.Collections.Generic.List[string]
$Results = New-Object System.Collections.Generic.List[string]

function Add-CheckResult {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][bool]$Passed,
        [Parameter(Mandatory = $false)][string]$Detail = ''
    )
    $Status = if ($Passed) { 'PASS' } else { 'FAIL' }
    $Line = '{0,-4} {1}' -f $Status, $Name
    if (-not [string]::IsNullOrEmpty($Detail)) {
        $Line = $Line + ' -- ' + $Detail
    }
    $Results.Add($Line)
    if (-not $Passed) { $Failures.Add($Name) }
}

$Repo = if ([string]::IsNullOrEmpty($RepoRoot)) {
    (Resolve-Path -LiteralPath '.').Path
} else {
    (Resolve-Path -LiteralPath $RepoRoot).Path
}
$ControllerPath = Join-Path $Repo 'scripts\provenance_controller.ps1'
$SelfCheckPath = Join-Path $Repo 'scripts\provenance_controller_selfcheck.ps1'
$DirectivePath = Join-Path $Repo (
    'HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md'
)

# --------------------------------------------------------------------------
# C1 - ASCII only (PS 5.1 parses a BOM-less script as ANSI)
# --------------------------------------------------------------------------
foreach ($Path in @($ControllerPath, $SelfCheckPath)) {
    $Bytes = [System.IO.File]::ReadAllBytes($Path)
    $NonAscii = @($Bytes | Where-Object { $_ -gt 127 })
    Add-CheckResult -Name ('C1 ascii-only: ' + (Split-Path $Path -Leaf)) `
        -Passed ($NonAscii.Count -eq 0) `
        -Detail ("non-ascii bytes=" + $NonAscii.Count)
}

# --------------------------------------------------------------------------
# C2 - Windows PowerShell 5.1 parser
# --------------------------------------------------------------------------
$ControllerAst = $null
foreach ($Path in @($ControllerPath, $SelfCheckPath)) {
    $Tokens = $null
    $ParseErrors = $null
    $Ast = [System.Management.Automation.Language.Parser]::ParseFile(
        $Path, [ref]$Tokens, [ref]$ParseErrors
    )
    if ($Path -eq $ControllerPath) { $ControllerAst = $Ast }
    $ErrorCount = @($ParseErrors).Count
    $Detail = if ($ErrorCount -eq 0) {
        'no parse errors'
    } else {
        [string]@($ParseErrors)[0].Message
    }
    Add-CheckResult -Name ('C2 parses on 5.1: ' + (Split-Path $Path -Leaf)) `
        -Passed ($ErrorCount -eq 0) -Detail $Detail
}

# --------------------------------------------------------------------------
# C3 - no function name shadowed by a built-in alias
#      (PowerShell resolves Alias before Function)
# --------------------------------------------------------------------------
if ($null -ne $ControllerAst) {
    $FunctionAsts = @($ControllerAst.FindAll(
        {
            param($Node)
            $Node -is [System.Management.Automation.Language.FunctionDefinitionAst]
        },
        $true
    ))
    $Collisions = New-Object System.Collections.Generic.List[string]
    foreach ($Function in $FunctionAsts) {
        $Alias = Get-Alias -Name $Function.Name -ErrorAction SilentlyContinue
        if ($null -ne $Alias) {
            $Collisions.Add(
                $Function.Name + '->' + $Alias.ResolvedCommandName
            )
        }
    }
    Add-CheckResult -Name 'C3 no alias-shadowed function names' `
        -Passed ($Collisions.Count -eq 0) `
        -Detail ("functions=" + $FunctionAsts.Count + " collisions=" +
            ($Collisions -join ','))
}

# --------------------------------------------------------------------------
# C4 - directive fence extraction reproduces the frozen appendix pins
# --------------------------------------------------------------------------
$DirectiveRaw = [System.IO.File]::ReadAllText($DirectivePath, $Utf8NoBom)
$DirectiveText = $DirectiveRaw -replace "`r`n", "`n"
Add-CheckResult -Name 'C4a directive has no lone CR' `
    -Passed (-not $DirectiveText.Contains([string][char]13))

function Get-SectionForCheck {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$HeadingPrefix
    )
    $HeadingPattern = '(?m)^' + [regex]::Escape($HeadingPrefix) + '[^\n]*$'
    $Headings = @([regex]::Matches($Text, $HeadingPattern))
    if ($Headings.Count -ne 1) {
        throw "heading cardinality $($Headings.Count): $HeadingPrefix"
    }
    $Start = $Headings[0].Index + $Headings[0].Length
    $Tail = $Text.Substring($Start)
    $NextHeading = [regex]::Match($Tail, '(?m)^#{2,3} [^\n]*$')
    if ($NextHeading.Success) {
        return $Tail.Substring(0, $NextHeading.Index)
    }
    return $Tail
}

function Get-FenceBodyForCheck {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$HeadingPrefix,
        [Parameter(Mandatory = $true)][string]$Language
    )
    $Section = Get-SectionForCheck -Text $Text -HeadingPrefix $HeadingPrefix
    $FencePattern = '(?ms)^```' + [regex]::Escape($Language) +
        "`n(.*?)^``````[ \t]*$"
    $Fences = @([regex]::Matches($Section, $FencePattern))
    if ($Fences.Count -ne 1) {
        throw "fence cardinality $($Fences.Count): $HeadingPrefix"
    }
    return ($Fences[0].Groups[1].Value.TrimEnd([char]10) + [string][char]10)
}

function Get-StringSha256 {
    param([Parameter(Mandatory = $true)][string]$Value)
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Bytes = $Hasher.ComputeHash($Utf8NoBom.GetBytes($Value))
    } finally {
        $Hasher.Dispose()
    }
    return (($Bytes | ForEach-Object { $_.ToString('x2') }) -join '')
}

$AssemblerFence = Get-FenceBodyForCheck -Text $DirectiveText `
    -HeadingPrefix '### 6.3 Exact evidence assembler invocation' `
    -Language 'powershell'
$Pins = @{}
foreach ($Row in @([regex]::Matches(
    $AssemblerFence, "'--appendix-([abc])-sha',\s*'([0-9a-f]{64})'"
))) {
    $Pins[$Row.Groups[1].Value] = $Row.Groups[2].Value
}
Add-CheckResult -Name 'C4b assembler pins parsed' `
    -Passed ($Pins.Count -eq 3) -Detail ("pins=" + $Pins.Count)

foreach ($Entry in @(
    @('a', '## Appendix A ', 'javascript'),
    @('b', '## Appendix B ', 'python'),
    @('c', '## Appendix C ', 'python')
)) {
    $Key = [string]$Entry[0]
    $Body = Get-FenceBodyForCheck -Text $DirectiveText `
        -HeadingPrefix ([string]$Entry[1]) -Language ([string]$Entry[2])
    $Derived = Get-StringSha256 -Value $Body
    $Expected = [string]$Pins[$Key]
    Add-CheckResult -Name ('C4c appendix ' + $Key.ToUpper() +
            ' derived == pinned') `
        -Passed ($Derived -ceq $Expected) `
        -Detail ('derived=' + $Derived.Substring(0, 12))
}

$ProbeSha = Get-StringSha256 -Value (
    Get-FenceBodyForCheck -Text $DirectiveText `
        -HeadingPrefix '## Appendix R ' -Language 'javascript'
)
$LedgerProbePin = [regex]::Match(
    $DirectiveText, "probe_source_sha256 =\s*\n?\s*'([0-9a-f]{64})'"
)
Add-CheckResult -Name 'C4d appendix R derived == ledger pin' `
    -Passed ($LedgerProbePin.Success -and
        ($ProbeSha -ceq $LedgerProbePin.Groups[1].Value)) `
    -Detail ('derived=' + $ProbeSha.Substring(0, 12))

# --------------------------------------------------------------------------
# C5 - setup fence placeholders substitute cleanly and the result parses
# --------------------------------------------------------------------------
$SetupBody = Get-FenceBodyForCheck -Text $DirectiveText `
    -HeadingPrefix '### 5.2 Exact PowerShell setup' -Language 'powershell'
$Substituted = $SetupBody.Replace(
    '<ENTRY_OR_RESUME>', 'ENTRY'
).Replace(
    '<DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256>', ('0' * 64)
).Replace(
    '<DISPATCH_EXACT_DIRECTIVE_RAW_SHA256>', ('1' * 64)
).Replace(
    '<DISPATCH_EXACT_DIRECTIVE_GIT_BLOB>', ('2' * 40)
)
Add-CheckResult -Name 'C5a setup placeholders all substituted' `
    -Passed (-not $Substituted.Contains('<DISPATCH_') -and
        -not $Substituted.Contains('<ENTRY_OR_'))

$SetupTokens = $null
$SetupErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseInput(
    $Substituted, [ref]$SetupTokens, [ref]$SetupErrors
)
$SetupErrorCount = @($SetupErrors).Count
Add-CheckResult -Name 'C5b substituted setup parses on 5.1' `
    -Passed ($SetupErrorCount -eq 0) `
    -Detail $(if ($SetupErrorCount -eq 0) {
        'no parse errors'
    } else {
        [string]@($SetupErrors)[0].Message
    })

# --------------------------------------------------------------------------
# C6 - every fence the controller dot-sources exists and parses
# --------------------------------------------------------------------------
foreach ($Heading in @(
    '### 2.4 Appendix byte materialization',
    '### 2.5 Actual phase ledger',
    '## 3. Entry Preflight',
    '### 4.3 P0 output rows',
    '### 5.3 Exact dry-run argv',
    '### 5.4 Exact isolated-export argv',
    '### 5.7 Exact analysis-only argv',
    '### 6.3 Exact evidence assembler invocation'
)) {
    $Ok = $true
    $Detail = ''
    try {
        $Body = Get-FenceBodyForCheck -Text $DirectiveText `
            -HeadingPrefix $Heading -Language 'powershell'
        $Body = $Body.Replace(
            '<DISPATCH_EXACT_DIRECTIVE_RAW_SHA256>', ('1' * 64)
        ).Replace(
            '<DISPATCH_EXACT_DIRECTIVE_GIT_BLOB>', ('2' * 40)
        ).Replace(
            '<DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256>', ('0' * 64)
        )
        $FenceTokens = $null
        $FenceErrors = $null
        $null = [System.Management.Automation.Language.Parser]::ParseInput(
            $Body, [ref]$FenceTokens, [ref]$FenceErrors
        )
        $Ok = (@($FenceErrors).Count -eq 0)
        $Detail = 'chars=' + $Body.Length
        if (-not $Ok) { $Detail = [string]@($FenceErrors)[0].Message }
    } catch {
        $Ok = $false
        $Detail = $_.Exception.Message
    }
    Add-CheckResult -Name ('C6 fence usable: ' + $Heading) `
        -Passed $Ok -Detail $Detail
}

# --------------------------------------------------------------------------
# C7 - frozen tables parse to the expected cardinality
# --------------------------------------------------------------------------
$ActorSection = Get-SectionForCheck -Text $DirectiveText `
    -HeadingPrefix '### 1.3 Producer actor set'
$ActorRows = @([regex]::Matches(
    $ActorSection,
    '(?m)^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|\s*$'
))
Add-CheckResult -Name 'C7a producer actor rows == 14' `
    -Passed ($ActorRows.Count -eq 14) -Detail ('rows=' + $ActorRows.Count)

$AuditSection = Get-SectionForCheck -Text $DirectiveText `
    -HeadingPrefix '### 1.2 Workbook and frozen audit'
$AuditByLabel = @{}
foreach ($Row in @([regex]::Matches(
    $AuditSection, '(?m)^\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*$'
))) {
    $AuditByLabel[$Row.Groups[1].Value] = $Row.Groups[2].Value
}
$AuditPaired = New-Object System.Collections.Generic.List[string]
foreach ($Label in @($AuditByLabel.Keys)) {
    $ShaLabel = $Label + ' SHA-256'
    if (-not $AuditByLabel.ContainsKey($ShaLabel)) { continue }
    if ([string]$AuditByLabel[$ShaLabel] -notmatch '^[0-9a-f]{64}$') {
        continue
    }
    $AuditPaired.Add([string]$AuditByLabel[$Label])
}
Add-CheckResult -Name 'C7b frozen audit label/SHA pairs == 4' `
    -Passed ($AuditPaired.Count -eq 4) `
    -Detail ('pairs=' + $AuditPaired.Count)

$AuditMissing = New-Object System.Collections.Generic.List[string]
foreach ($Relative in $AuditPaired) {
    $Absolute = Join-Path $Repo ($Relative -replace '/', '\')
    if (-not (Test-Path -LiteralPath $Absolute -PathType Leaf)) {
        $AuditMissing.Add($Relative)
    }
}
Add-CheckResult -Name 'C7c frozen audit files present' `
    -Passed ($AuditMissing.Count -eq 0) `
    -Detail ('missing=' + ($AuditMissing -join ','))

# --------------------------------------------------------------------------
# C8 - controller orchestration is authorized and timeout-bound by directive
# --------------------------------------------------------------------------
$AllowlistSection = Get-SectionForCheck -Text $DirectiveText `
    -HeadingPrefix '### 2.3 Closed tool-call allowlist'
$PrepareOperation = (
    'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe ' +
    '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass ' +
    '-File scripts\provenance_controller.ps1 -Mode prepare ' +
    '-CapsuleSha256 <DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256> ' +
    '-RepoRoot C:\Users\momen\Projects\tc-runner'
)
$ResumeOperation = (
    'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe ' +
    '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass ' +
    '-File scripts\provenance_controller.ps1 -Mode resume ' +
    '-CapsuleSha256 <DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256> ' +
    '-RepoRoot C:\Users\momen\Projects\tc-runner'
)
$PrepareCount = @([regex]::Matches(
    $AllowlistSection,
    [regex]::Escape($PrepareOperation)
)).Count
$ResumeCount = @([regex]::Matches(
    $AllowlistSection,
    [regex]::Escape($ResumeOperation)
)).Count
Add-CheckResult -Name 'C8a prepare controller operation authorized once' `
    -Passed ($PrepareCount -eq 1) -Detail ('count=' + $PrepareCount)
Add-CheckResult -Name 'C8b resume controller operation authorized once' `
    -Passed ($ResumeCount -eq 1) -Detail ('count=' + $ResumeCount)

$EntrySection = Get-SectionForCheck -Text $DirectiveText `
    -HeadingPrefix '## 3. Entry Preflight'
$P1SetupSection = Get-SectionForCheck -Text $DirectiveText `
    -HeadingPrefix '### 5.2 Exact PowerShell setup'
$AssemblerSection = Get-SectionForCheck -Text $DirectiveText `
    -HeadingPrefix '### 6.3 Exact evidence assembler invocation'
$SequencingBound = (
    $EntrySection.Contains('controller prepare operation') -and
    $EntrySection.Contains('controller resume operation') -and
    $P1SetupSection.Contains('controller resume operation') -and
    $AssemblerSection.Contains('controller resume operation')
)
Add-CheckResult -Name 'C8c prepare/resume sequencing is controller-bound' `
    -Passed $SequencingBound

$PrepareTimeout = [regex]::Match(
    $P1SetupSection,
    '(?m)^\| `prepare` \| `([0-9]+)` \|$'
)
$ResumeTimeout = [regex]::Match(
    $P1SetupSection,
    '(?m)^\| `resume` \| `([0-9]+)` \|$'
)
$TimeoutsBound = (
    $PrepareTimeout.Success -and $ResumeTimeout.Success -and
    [int64]$PrepareTimeout.Groups[1].Value -ge 300000 -and
    [int64]$ResumeTimeout.Groups[1].Value -ge 1800000 -and
    $P1SetupSection.Contains('50 seconds or less')
)
Add-CheckResult -Name 'C8d outer controller timeout/yield contract pinned' `
    -Passed $TimeoutsBound

# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
foreach ($Line in $Results) { [Console]::Out.WriteLine($Line) }
[Console]::Out.WriteLine('')
if ($Failures.Count -eq 0) {
    [Console]::Out.WriteLine(
        'SELFCHECK GREEN (' + $Results.Count + ' checks)'
    )
    exit 0
}
[Console]::Out.WriteLine(
    'SELFCHECK FAILED (' + $Failures.Count + '/' + $Results.Count + ')'
)
exit 1

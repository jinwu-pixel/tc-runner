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

$AssemblerHelperCount = @([regex]::Matches(
    $AssemblerFence,
    '(?m)^\$AssembleResult = Invoke-ControllerProcess '
)).Count
Add-CheckResult -Name 'C8e assembler uses controller process helper once' `
    -Passed ($AssemblerHelperCount -eq 1) `
    -Detail ('count=' + $AssemblerHelperCount)

$DirectAssemblerCount = @([regex]::Matches(
    $AssemblerFence,
    '(?m)^& \$Python @AssembleArgs$'
)).Count
Add-CheckResult -Name 'C8f assembler forbids direct native invocation' `
    -Passed ($DirectAssemblerCount -eq 0) `
    -Detail ('count=' + $DirectAssemblerCount)

$AssemblerResultPreserved = (
    $AssemblerFence.Contains(
        '[Console]::Out.Write($AssembleResult.StandardOutput)'
    ) -and
    $AssemblerFence.Contains(
        '[Console]::Error.Write($AssembleResult.StandardError)'
    ) -and
    $AssemblerFence.Contains(
        '$CampaignExit = [int]$AssembleResult.ExitCode'
    )
)
Add-CheckResult -Name 'C8g assembler preserves stdout stderr and exit' `
    -Passed $AssemblerResultPreserved

# --------------------------------------------------------------------------
# C9 - producer reconciliation manifest and identity namespaces
# --------------------------------------------------------------------------
$AppendixA = Get-FenceBodyForCheck -Text $DirectiveText `
    -HeadingPrefix '## Appendix A ' -Language 'javascript'
$AppendixB = Get-FenceBodyForCheck -Text $DirectiveText `
    -HeadingPrefix '## Appendix B ' -Language 'python'
$AppendixC = Get-FenceBodyForCheck -Text $DirectiveText `
    -HeadingPrefix '## Appendix C ' -Language 'python'

$ExpectedYamlCount = 12
$ExpectedSelectorCount = 14
$ExpectedBlockerCount = 15
$ExpectedSourceDistribution = @{ 'SS-TC 0' = 1; 'SS-TC 1' = 13 }
$ExpectedBlockerDistribution = @{ 'SS-TC 0' = 1; 'SS-TC 1' = 14 }

$TargetMatch = [regex]::Match(
    $AppendixA,
    '(?ms)^\s*const TARGETS = (?<body>.*?);\n\s*const HEADER_PATTERNS'
)
$TargetBody = if ($TargetMatch.Success) {
    $TargetMatch.Groups['body'].Value
} else {
    ''
}
$PathPattern = 'exported_ss_call/[A-Za-z0-9_]+\.yaml'
$YamlPaths = @(
    [regex]::Matches($TargetBody, $PathPattern) |
        ForEach-Object { $_.Value } |
        Select-Object -Unique
)
$SelectorPattern = (
    '\{\s*"?source_no"?\s*:\s*"(?<source>[^"\r\n]+)"\s*,' +
    '\s*"?source_functionality_effective"?\s*:'
)
$BlockerPattern = (
    '\{\s*"?blocker_step_index"?\s*:\s*(?<step>[0-9]+)\s*,' +
    '\s*"?source_no"?\s*:\s*"(?<source>[^"\r\n]+)"\s*\}'
)
$SelectorMatches = @([regex]::Matches($TargetBody, $SelectorPattern))
$BlockerMatches = @([regex]::Matches($TargetBody, $BlockerPattern))
Add-CheckResult -Name 'C9a manifest cardinality is 12/14/15' `
    -Passed (
        $YamlPaths.Count -eq $ExpectedYamlCount -and
        $SelectorMatches.Count -eq $ExpectedSelectorCount -and
        $BlockerMatches.Count -eq $ExpectedBlockerCount
    ) `
    -Detail (
        'yaml=' + $YamlPaths.Count + ',selectors=' +
        $SelectorMatches.Count + ',blockers=' + $BlockerMatches.Count
    )

$SourceDistribution = @{ 'SS-TC 0' = 0; 'SS-TC 1' = 0 }
$BlockerDistribution = @{ 'SS-TC 0' = 0; 'SS-TC 1' = 0 }
$PathMatches = @([regex]::Matches($TargetBody, $PathPattern))
$AggregateSegment = ''
for ($Index = 0; $Index -lt $PathMatches.Count; $Index++) {
    $Start = $PathMatches[$Index].Index
    $End = if ($Index + 1 -lt $PathMatches.Count) {
        $PathMatches[$Index + 1].Index
    } else {
        $TargetBody.Length
    }
    $Segment = $TargetBody.Substring($Start, $End - $Start)
    $SheetMatch = [regex]::Match(
        $Segment, '"?sheet"?\s*:\s*"(?<sheet>SS-TC [01])"'
    )
    if ($SheetMatch.Success) {
        $Sheet = $SheetMatch.Groups['sheet'].Value
        $SourceDistribution[$Sheet] += @(
            [regex]::Matches($Segment, $SelectorPattern)
        ).Count
        $BlockerDistribution[$Sheet] += @(
            [regex]::Matches($Segment, $BlockerPattern)
        ).Count
    }
    if ($PathMatches[$Index].Value -eq
        'exported_ss_call/SS_TC05_boundary_values.yaml') {
        $AggregateSegment = $Segment
    }
}
$DistributionMatches = $true
foreach ($Sheet in @('SS-TC 0', 'SS-TC 1')) {
    if (
        $SourceDistribution[$Sheet] -ne $ExpectedSourceDistribution[$Sheet] -or
        $BlockerDistribution[$Sheet] -ne
            $ExpectedBlockerDistribution[$Sheet]
    ) {
        $DistributionMatches = $false
    }
}
Add-CheckResult -Name 'C9b source/blocker distribution is 1+13/1+14' `
    -Passed $DistributionMatches `
    -Detail (
        'sources=' + $SourceDistribution['SS-TC 0'] + '+' +
        $SourceDistribution['SS-TC 1'] + ',blockers=' +
        $BlockerDistribution['SS-TC 0'] + '+' +
        $BlockerDistribution['SS-TC 1']
    )

$AggregateSelectors = @(
    [regex]::Matches($AggregateSegment, $SelectorPattern) |
        ForEach-Object { $_.Groups['source'].Value }
)
$AggregateBindings = @(
    [regex]::Matches($AggregateSegment, $BlockerPattern) |
        ForEach-Object {
            $_.Groups['step'].Value + ':' + $_.Groups['source'].Value
        }
)
Add-CheckResult -Name 'C9c SS_TC05 A/B/C and step 9 to A only' `
    -Passed (
        (($AggregateSelectors -join ',') -ceq 'TC-05A,TC-05B,TC-05C') -and
        (($AggregateBindings -join ',') -ceq '9:TC-05A')
    ) `
    -Detail (
        'selectors=' + ($AggregateSelectors -join ',') +
        ',bindings=' + ($AggregateBindings -join ',')
    )

$ForbiddenJoins = @(
    'row.tc_name === target.yaml_tc_name',
    'mapping.get("yaml_tc_name") != expected_tc_name',
    'emitted.get("name") == tc_name'
)
$ObservedForbidden = New-Object System.Collections.Generic.List[string]
foreach ($Needle in $ForbiddenJoins) {
    if (
        $AppendixA.Contains($Needle) -or
        $AppendixB.Contains($Needle) -or
        $AppendixC.Contains($Needle)
    ) {
        $ObservedForbidden.Add($Needle)
    }
}
Add-CheckResult -Name 'C9d direct alias joins are forbidden' `
    -Passed ($ObservedForbidden.Count -eq 0) `
    -Detail ('observed=' + $ObservedForbidden.Count)

$P0SchemaV3 = (
    $AppendixA.Contains('schema_version: 3,') -and
    $AppendixC.Contains('p0.get("schema_version") == 3') -and
    $AppendixC.Contains('p0.get("schema_version") != 3')
)
Add-CheckResult -Name 'C9e P0 schema version is 3 end-to-end' `
    -Passed $P0SchemaV3

$ReconciliationSchemaV2 = $AppendixC.Contains(
    'value.get("schema_version") != 2'
)
Add-CheckResult -Name 'C9f reconciliation schema version is 2' `
    -Passed $ReconciliationSchemaV2

$SplitIdentity = (
    $AppendixB.Contains(
        'emitted.get("name") == workbook_tc_name'
    ) -and
    $AppendixB.Contains(
        'tracked.get("tc_name") == yaml_tc_name'
    )
)
Add-CheckResult -Name 'C9g producer and tracked identities stay split' `
    -Passed $SplitIdentity

$SharedColumnContract = (
    $AppendixB.Contains('def valid_semantic_column_map(') -and
    $AppendixB.Contains('{"feature_name", "priority"}') -and
    $AppendixB.Contains(
        'column_map["feature_name"] == column_map["functionality"] - 1'
    ) -and
    $AppendixB.Contains('def assert_shared_coordinate_evidence(') -and
    $AppendixB.Contains(
        'assert_shared_coordinate_evidence(cells, "cell")'
    ) -and
    $AppendixB.Contains(
        'assert_shared_coordinate_evidence(region_records, "region")'
    ) -and
    $AppendixB.Contains(
        'f"shared semantic {evidence_label} evidence differs: "'
    )
)
Add-CheckResult -Name 'C9h loader alias is narrow and evidence-identical' `
    -Passed $SharedColumnContract

$AnalyzeSummaryContract = (
    $AppendixB.Contains('"ANALYZE_RESULT "') -and
    $AppendixB.Contains('f"verdict={output[''verdict'']} "') -and
    $AppendixB.Contains(
        'f"mapped_documents={len(mapped_document_status)} "'
    ) -and
    $AppendixB.Contains('f"targets={len(targets)} "') -and
    $AppendixB.Contains('f"blocking_reasons={len(reasons)}"')
)
Add-CheckResult -Name 'C9i analyzer emits deterministic nonempty summary' `
    -Passed $AnalyzeSummaryContract

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

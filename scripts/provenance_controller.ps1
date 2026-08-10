# Provenance campaign controller for RB-20260728-shellrc-p0p1.
#
# This script replaces hand-synthesized controller glue. It extracts the
# directive's own exact code fences and executes them in the specified
# order, implementing only the prose-specified sequencing around them.
#
# ASCII-only by contract: Windows PowerShell 5.1 reads a BOM-less .ps1 as
# ANSI, so any non-ASCII byte here would be mangled at parse time.
# Enforced by scripts/provenance_controller_selfcheck.ps1.
#
# Modes:
#   prepare  host preflight -> temp root -> ledger -> appendix B/C
#   resume   P0 gate -> P1 -> evidence assembly (campaign exit)
#
# Between the two modes the executor submits Appendix R (module-route
# negative control, with at most one js_add_node_module_dir) and then
# Appendix A (P0 capture) to node_repl.js. Those are MCP tool calls and
# cannot be performed from PowerShell.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('prepare', 'resume', 'selftest')]
    [string]$Mode,

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^([0-9a-f]{64})?$')]
    [string]$CapsuleSha256 = '',

    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = '',

    # Rehearsal only: redirects the external temp root and the evidence
    # root so the full driver can be exercised without touching the real
    # campaign paths. Never used for a dispatched campaign.
    [Parameter(Mandatory = $false)]
    [string]$RehearsalRoot = '',

    # Rehearsal only: skips the one-time capsule verifier subprocess.
    [Parameter(Mandatory = $false)]
    [switch]$RehearsalSkipVerify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EXIT_INPUT_INVALID = 2
$EXIT_INFRA_FAILURE = 3

$ControllerUtf8NoBom = New-Object System.Text.UTF8Encoding($false)
$DirectiveRelativePath = 'HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md'
$ExpectedToplevel = 'C:/Users/momen/Projects/tc-runner'
$FrozenTempRoot =
    'C:\tmp\tc-runner-shell-rc-provenance-RB-20260728-shellrc-p0p1'
$FrozenEvidenceRelative =
    'reports/canonical_shell_rc_provenance/RB-20260728-shellrc-p0p1'

# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------

function New-ControllerFailure {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][bool]$InputInvalid
    )
    $Prefix = if ($InputInvalid) { 'INPUT_MISMATCH: ' } else { 'INFRA: ' }
    return (New-Object System.InvalidOperationException(
        $Prefix + $Message
    ))
}

function Test-ControllerInputMismatch {
    param([Parameter(Mandatory = $true)][System.Exception]$Exception)
    return $Exception.Message.StartsWith(
        'INPUT_MISMATCH: ',
        [System.StringComparison]::Ordinal
    )
}

function Get-ControllerExitCode {
    param([Parameter(Mandatory = $true)][System.Exception]$Exception)
    if (Test-ControllerInputMismatch -Exception $Exception) {
        return $EXIT_INPUT_INVALID
    }
    return $EXIT_INFRA_FAILURE
}

# ---------------------------------------------------------------------------
# Directive parsing (single source of truth for every frozen literal)
# ---------------------------------------------------------------------------

function Get-DirectiveText {
    param([Parameter(Mandatory = $true)][string]$Path)
    $Raw = [System.IO.File]::ReadAllText($Path, $ControllerUtf8NoBom)
    $Normalized = $Raw -replace "`r`n", "`n"
    if ($Normalized.Contains([string][char]13)) {
        throw (New-ControllerFailure `
            -Message 'directive contains lone CR' -InputInvalid $true)
    }
    return $Normalized
}

function Get-DirectiveSectionText {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$HeadingPrefix
    )
    $Pattern = '(?m)^' + [regex]::Escape($HeadingPrefix) + '[^\n]*$'
    $Matches = @([regex]::Matches($Text, $Pattern))
    if ($Matches.Count -ne 1) {
        throw (New-ControllerFailure `
            -Message ("heading cardinality " + $Matches.Count +
                " for '" + $HeadingPrefix + "'") `
            -InputInvalid $true)
    }
    $Start = $Matches[0].Index + $Matches[0].Length
    $Tail = $Text.Substring($Start)
    $NextHeading = [regex]::Match($Tail, '(?m)^#{2,3} [^\n]*$')
    if ($NextHeading.Success) {
        return $Tail.Substring(0, $NextHeading.Index)
    }
    return $Tail
}

function Get-DirectiveFenceBody {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$HeadingPrefix,
        [Parameter(Mandatory = $true)][string]$Language,
        [Parameter(Mandatory = $false)][int]$Index = 0,
        [Parameter(Mandatory = $false)][bool]$ExpectSingle = $true
    )
    $Section = Get-DirectiveSectionText -Text $Text -HeadingPrefix $HeadingPrefix
    $Pattern = '(?ms)^```' + [regex]::Escape($Language) +
        "`n(.*?)^``````[ \t]*$"
    $Fences = @([regex]::Matches($Section, $Pattern))
    if ($ExpectSingle -and $Fences.Count -ne 1) {
        throw (New-ControllerFailure `
            -Message ("fence cardinality " + $Fences.Count +
                " for '" + $HeadingPrefix + "'") `
            -InputInvalid $true)
    }
    if ($Fences.Count -le $Index) {
        throw (New-ControllerFailure `
            -Message ("fence index " + $Index + " absent for '" +
                $HeadingPrefix + "'") `
            -InputInvalid $true)
    }
    $Body = $Fences[$Index].Groups[1].Value
    return ($Body.TrimEnd([char]10) + [string][char]10)
}

function Get-Sha256OfString {
    param([Parameter(Mandatory = $true)][string]$Value)
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Bytes = $Hasher.ComputeHash($ControllerUtf8NoBom.GetBytes($Value))
    } finally {
        $Hasher.Dispose()
    }
    return (($Bytes | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Get-Sha256OfFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path
        ).Hash.ToLowerInvariant()
}

function Get-DirectiveTablePairs {
    # Parses two-column markdown rows whose cells are backtick-quoted,
    # e.g. "| `src/cli.py` | `<sha>` |".
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$HeadingPrefix
    )
    $Section = Get-DirectiveSectionText -Text $Text -HeadingPrefix $HeadingPrefix
    $Pairs = [ordered]@{}
    $Pattern = '(?m)^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|\s*$'
    foreach ($Row in @([regex]::Matches($Section, $Pattern))) {
        $Key = $Row.Groups[1].Value
        if ($Pairs.Contains($Key)) {
            throw (New-ControllerFailure `
                -Message "duplicate table key: $Key" -InputInvalid $true)
        }
        $Pairs[$Key] = $Row.Groups[2].Value
    }
    return $Pairs
}

function Get-FrozenAuditPairs {
    # Section 1.2 pairs a "<label>" row with a "<label> SHA-256" row.
    param([Parameter(Mandatory = $true)][string]$Text)
    $Section = Get-DirectiveSectionText -Text $Text `
        -HeadingPrefix '### 1.2 Workbook and frozen audit'
    $Rows = @([regex]::Matches(
        $Section,
        '(?m)^\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*$'
    ))
    $ByLabel = [ordered]@{}
    foreach ($Row in $Rows) {
        $ByLabel[$Row.Groups[1].Value] = $Row.Groups[2].Value
    }
    $Pairs = [ordered]@{}
    foreach ($Label in @($ByLabel.Keys)) {
        $ShaLabel = $Label + ' SHA-256'
        if (-not $ByLabel.Contains($ShaLabel)) { continue }
        $Value = [string]$ByLabel[$Label]
        $Sha = [string]$ByLabel[$ShaLabel]
        if ($Sha -notmatch '^[0-9a-f]{64}$') { continue }
        $Pairs[$Value] = $Sha
    }
    if ($Pairs.Count -ne 4) {
        throw (New-ControllerFailure `
            -Message ("frozen audit pair count " + $Pairs.Count) `
            -InputInvalid $true)
    }
    return $Pairs
}

function Get-AssemblerAppendixPins {
    param([Parameter(Mandatory = $true)][string]$Text)
    $Fence = Get-DirectiveFenceBody -Text $Text `
        -HeadingPrefix '### 6.3 Exact evidence assembler invocation' `
        -Language 'powershell'
    $Pins = [ordered]@{}
    foreach ($Row in @([regex]::Matches(
        $Fence,
        "'--appendix-([abc])-sha',\s*'([0-9a-f]{64})'"
    ))) {
        $Pins[$Row.Groups[1].Value] = $Row.Groups[2].Value
    }
    if ($Pins.Count -ne 3) {
        throw (New-ControllerFailure `
            -Message ("assembler appendix pin count " + $Pins.Count) `
            -InputInvalid $true)
    }
    return $Pins
}

# ---------------------------------------------------------------------------
# Read-only git helpers (pre-setup; the directive fence defines its own once
# it has been dot-sourced)
# ---------------------------------------------------------------------------

function ConvertTo-ProcessArgumentString {
    # Windows PowerShell 5.1 runs on .NET Framework, where
    # ProcessStartInfo exposes only the single Arguments string, so each
    # argument is quoted here per CommandLineToArgvW rules.
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()]
        [string[]]$ArgumentList
    )
    $Parts = New-Object System.Collections.Generic.List[string]
    foreach ($Argument in $ArgumentList) {
        $Special = [char[]]@([char]32, [char]9, [char]34)
        if ($Argument.Length -gt 0 -and
            $Argument.IndexOfAny($Special) -lt 0) {
            $Parts.Add($Argument)
            continue
        }
        $Builder = New-Object System.Text.StringBuilder
        [void]$Builder.Append('"')
        $Backslashes = 0
        foreach ($Character in $Argument.ToCharArray()) {
            if ($Character -eq [char]92) {
                $Backslashes = $Backslashes + 1
                continue
            }
            if ($Character -eq [char]34) {
                [void]$Builder.Append('\' * ($Backslashes * 2 + 1))
                $Backslashes = 0
                [void]$Builder.Append('"')
                continue
            }
            if ($Backslashes -gt 0) {
                [void]$Builder.Append('\' * $Backslashes)
                $Backslashes = 0
            }
            [void]$Builder.Append($Character)
        }
        [void]$Builder.Append('\' * ($Backslashes * 2))
        [void]$Builder.Append('"')
        $Parts.Add($Builder.ToString())
    }
    return ($Parts -join ' ')
}

function Invoke-ControllerProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][AllowEmptyString()]
        [string[]]$ArgumentList,
        [Parameter(Mandatory = $false)][string]$WorkingDirectory = ''
    )
    $StartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $StartInfo.FileName = $FilePath
    $StartInfo.Arguments =
        ConvertTo-ProcessArgumentString -ArgumentList $ArgumentList
    if (-not [string]::IsNullOrEmpty($WorkingDirectory)) {
        $StartInfo.WorkingDirectory = $WorkingDirectory
    }
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.StandardOutputEncoding = $ControllerUtf8NoBom
    $StartInfo.StandardErrorEncoding = $ControllerUtf8NoBom
    $Process = New-Object System.Diagnostics.Process
    $Process.StartInfo = $StartInfo
    if (-not $Process.Start()) {
        throw (New-ControllerFailure `
            -Message "process failed to start: $FilePath" `
            -InputInvalid $false)
    }
    $OutTask = $Process.StandardOutput.ReadToEndAsync()
    $ErrTask = $Process.StandardError.ReadToEndAsync()
    $Process.WaitForExit()
    return [pscustomobject]@{
        ExitCode = $Process.ExitCode
        StandardOutput = $OutTask.GetAwaiter().GetResult()
        StandardError = $ErrTask.GetAwaiter().GetResult()
    }
}

function Invoke-ControllerGit {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][AllowEmptyString()]
        [string[]]$ArgumentList,
        [Parameter(Mandatory = $false)][int[]]$AllowedExitCodes = @(0)
    )
    $FullArguments = @('-c', 'core.excludesFile=NUL') + $ArgumentList
    $Previous = @{
        GIT_CONFIG_GLOBAL = $env:GIT_CONFIG_GLOBAL
        GIT_CONFIG_SYSTEM = $env:GIT_CONFIG_SYSTEM
    }
    $env:GIT_CONFIG_GLOBAL = 'NUL'
    $env:GIT_CONFIG_SYSTEM = 'NUL'
    try {
        $Result = Invoke-ControllerProcess -FilePath 'git' `
            -ArgumentList $FullArguments -WorkingDirectory $RepoPath
    } finally {
        $env:GIT_CONFIG_GLOBAL = $Previous.GIT_CONFIG_GLOBAL
        $env:GIT_CONFIG_SYSTEM = $Previous.GIT_CONFIG_SYSTEM
    }
    if ($AllowedExitCodes -notcontains $Result.ExitCode) {
        throw (New-ControllerFailure `
            -Message ("git " + ($ArgumentList -join ' ') + " exit " +
                $Result.ExitCode + ": " + $Result.StandardError.Trim()) `
            -InputInvalid $false)
    }
    return $Result
}

function Get-WorkbookMtimeNs {
    param([Parameter(Mandatory = $true)][string]$Path)
    $Item = Get-Item -LiteralPath $Path
    $EpochTicks = [System.Numerics.BigInteger]621355968000000000
    return ((
        [System.Numerics.BigInteger]$Item.LastWriteTimeUtc.Ticks - $EpochTicks
    ) * [System.Numerics.BigInteger]100).ToString()
}

# ---------------------------------------------------------------------------
# Section 3 host preflight items 4-10 (items 1-3, 11, 12 live in the
# directive's own setup fence and run during dot-source)
# ---------------------------------------------------------------------------

function Assert-HostPreflightItems {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][string]$DirectiveText,
        [Parameter(Mandatory = $true)][string]$WorkbookPath,
        [Parameter(Mandatory = $true)][string]$PythonPath,
        [Parameter(Mandatory = $true)][string]$TempRootPath,
        [Parameter(Mandatory = $true)][string]$EvidenceRunDir
    )
    $Observed = [ordered]@{}

    # item 4 - repository toplevel
    $Toplevel = (Invoke-ControllerGit -RepoPath $RepoPath `
        -ArgumentList @('rev-parse', '--show-toplevel')
        ).StandardOutput.Trim()
    if (($Toplevel -replace '\\', '/') -ne $ExpectedToplevel) {
        throw (New-ControllerFailure `
            -Message "repository toplevel mismatch: $Toplevel" `
            -InputInvalid $true)
    }

    # items 5-6 - workbook identity and mtime-before
    $FrozenAudit = Get-FrozenAuditPairs -Text $DirectiveText
    $WorkbookRelative = 'tc_samples/TC_1.xlsx'
    $WorkbookFrozenSha = $null
    $WorkbookFrozenBlob = $null
    $Section12 = Get-DirectiveSectionText -Text $DirectiveText `
        -HeadingPrefix '### 1.2 Workbook and frozen audit'
    $ShaRow = [regex]::Match(
        $Section12,
        '(?m)^\|\s*workbook raw SHA-256\s*\|\s*`([0-9a-f]{64})`\s*\|\s*$'
    )
    $BlobRow = [regex]::Match(
        $Section12,
        '(?m)^\|\s*workbook Git blob\s*\|\s*`([0-9a-f]{40})`\s*\|\s*$'
    )
    if (-not $ShaRow.Success -or -not $BlobRow.Success) {
        throw (New-ControllerFailure `
            -Message 'workbook freeze rows not found' -InputInvalid $true)
    }
    $WorkbookFrozenSha = $ShaRow.Groups[1].Value
    $WorkbookFrozenBlob = $BlobRow.Groups[1].Value

    $null = Invoke-ControllerGit -RepoPath $RepoPath -ArgumentList @(
        'ls-files', '--error-unmatch', '--', $WorkbookRelative
    )
    $WorkbookSha = Get-Sha256OfFile -Path $WorkbookPath
    if ($WorkbookSha -ne $WorkbookFrozenSha) {
        throw (New-ControllerFailure `
            -Message "workbook raw SHA mismatch: $WorkbookSha" `
            -InputInvalid $true)
    }
    $WorkbookBlob = (Invoke-ControllerGit -RepoPath $RepoPath -ArgumentList @(
        'hash-object', '--no-filters', '--', $WorkbookRelative
    )).StandardOutput.Trim()
    if ($WorkbookBlob -ne $WorkbookFrozenBlob) {
        throw (New-ControllerFailure `
            -Message "workbook blob mismatch: $WorkbookBlob" `
            -InputInvalid $true)
    }
    $WorktreeClean = (Invoke-ControllerGit -RepoPath $RepoPath -ArgumentList @(
        'diff', '--quiet', '--', $WorkbookRelative
    ) -AllowedExitCodes @(0, 1)).ExitCode -eq 0
    $IndexClean = (Invoke-ControllerGit -RepoPath $RepoPath -ArgumentList @(
        'diff', '--cached', '--quiet', '--', $WorkbookRelative
    ) -AllowedExitCodes @(0, 1)).ExitCode -eq 0
    if (-not $WorktreeClean -or -not $IndexClean) {
        throw (New-ControllerFailure `
            -Message 'workbook worktree/index differs from HEAD' `
            -InputInvalid $true)
    }
    $Observed['workbook_raw_sha256'] = $WorkbookSha
    $Observed['workbook_blob'] = $WorkbookBlob
    $Observed['workbook_mtime_before_ns'] =
        Get-WorkbookMtimeNs -Path $WorkbookPath

    # item 7 - frozen audit artefacts
    foreach ($Entry in $FrozenAudit.GetEnumerator()) {
        $Relative = [string]$Entry.Key
        $Expected = [string]$Entry.Value
        $Absolute = Join-Path $RepoPath ($Relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $Absolute -PathType Leaf)) {
            throw (New-ControllerFailure `
                -Message "frozen audit file missing: $Relative" `
                -InputInvalid $true)
        }
        $Actual = Get-Sha256OfFile -Path $Absolute
        if ($Actual -ne $Expected) {
            throw (New-ControllerFailure `
                -Message "frozen audit hash mismatch: $Relative" `
                -InputInvalid $true)
        }
    }

    # item 8 - producer actor set
    $Actors = Get-DirectiveTablePairs -Text $DirectiveText `
        -HeadingPrefix '### 1.3 Producer actor set'
    if ($Actors.Count -ne 14) {
        throw (New-ControllerFailure `
            -Message ("producer actor count " + $Actors.Count) `
            -InputInvalid $true)
    }
    foreach ($Entry in $Actors.GetEnumerator()) {
        $Relative = [string]$Entry.Key
        $Absolute = Join-Path $RepoPath ($Relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $Absolute -PathType Leaf)) {
            throw (New-ControllerFailure `
                -Message "producer actor missing: $Relative" `
                -InputInvalid $true)
        }
        $Actual = Get-Sha256OfFile -Path $Absolute
        if ($Actual -ne [string]$Entry.Value) {
            throw (New-ControllerFailure `
                -Message "producer actor hash mismatch: $Relative" `
                -InputInvalid $true)
        }
    }

    # item 9 - toolchain versions and process encoding
    $Toolchain = Get-ToolchainObservation -RepoPath $RepoPath `
        -PythonPath $PythonPath -DirectiveText $DirectiveText
    $Observed['toolchain'] = $Toolchain

    # item 10 - temp/evidence absence and evidence ignore rule
    if (Test-Path -LiteralPath $TempRootPath) {
        throw (New-ControllerFailure `
            -Message "temp root already exists: $TempRootPath" `
            -InputInvalid $true)
    }
    if (Test-Path -LiteralPath $EvidenceRunDir) {
        throw (New-ControllerFailure `
            -Message "evidence run directory already exists" `
            -InputInvalid $true)
    }
    $EvidenceFileRelative = $FrozenEvidenceRelative + '/PROVENANCE_EVIDENCE.json'
    $CheckIgnore = Invoke-ControllerGit -RepoPath $RepoPath -ArgumentList @(
        'check-ignore', '-v', '--', $EvidenceFileRelative
    ) -AllowedExitCodes @(0, 1)
    if ($CheckIgnore.ExitCode -ne 0) {
        throw (New-ControllerFailure `
            -Message 'evidence path is not ignored' -InputInvalid $true)
    }
    $Observed['evidence_ignore_rule'] = $CheckIgnore.StandardOutput.Trim()

    return $Observed
}

function Get-ToolchainObservation {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][string]$PythonPath,
        [Parameter(Mandatory = $true)][string]$DirectiveText
    )
    $PythonVersion = (Invoke-ControllerProcess -FilePath $PythonPath `
        -ArgumentList @('-B', '--version') -WorkingDirectory $RepoPath
        ).StandardOutput.Trim()
    $PythonVersion = $PythonVersion -replace '^Python\s+', ''
    $LibraryProbe = Invoke-ControllerProcess -FilePath $PythonPath `
        -ArgumentList @(
            '-B', '-c',
            ('import openpyxl, yaml; print(openpyxl.__version__); ' +
                'print(yaml.__version__)')
        ) -WorkingDirectory $RepoPath
    $LibraryLines = @(
        $LibraryProbe.StandardOutput -split "`r?`n" |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($LibraryProbe.ExitCode -ne 0 -or $LibraryLines.Count -ne 2) {
        throw (New-ControllerFailure `
            -Message ('python library version probe failed: exit=' +
                $LibraryProbe.ExitCode + ' stdout=[' +
                $LibraryProbe.StandardOutput.Trim() + '] stderr=[' +
                $LibraryProbe.StandardError.Trim() + ']') `
            -InputInvalid $false)
    }
    $NodeVersion = (Invoke-ControllerProcess -FilePath 'node' `
        -ArgumentList @('--version') -WorkingDirectory $RepoPath
        ).StandardOutput.Trim()

    $Observed = [ordered]@{
        console_input = 'utf-8'
        console_output = 'utf-8'
        node = $NodeVersion
        openpyxl = $LibraryLines[0].Trim()
        output_encoding = 'utf-8'
        powershell = $PSVersionTable.PSVersion.ToString()
        psedition = [string]$PSVersionTable.PSEdition
        pyyaml = $LibraryLines[1].Trim()
        python = $PythonVersion
        pythonhashseed = '0'
        pythonioencoding = 'utf-8'
    }

    # The directive freezes the exact toolchain object; compare field by
    # field so a drifted interpreter is an input mismatch, not a silent pass.
    $Expected = Get-DirectiveFenceBody -Text $DirectiveText `
        -HeadingPrefix '### 2.5 Actual phase ledger' -Language 'json' |
        ConvertFrom-Json
    foreach ($Name in @($Expected.PSObject.Properties.Name)) {
        $ExpectedValue = [string]$Expected.$Name
        $ActualValue = [string]$Observed[$Name]
        if ($ActualValue -cne $ExpectedValue) {
            throw (New-ControllerFailure `
                -Message ("toolchain mismatch for " + $Name + ": " +
                    $ActualValue + " != " + $ExpectedValue) `
                -InputInvalid $true)
        }
    }
    return $Observed
}

# ---------------------------------------------------------------------------
# Directive setup fence
# ---------------------------------------------------------------------------

function Import-DirectiveSetup {
    param(
        [Parameter(Mandatory = $true)][string]$DirectiveText,
        [Parameter(Mandatory = $true)][string]$EntryMode,
        [Parameter(Mandatory = $true)][string]$CapsuleToken,
        [Parameter(Mandatory = $true)][string]$DirectiveRawSha256,
        [Parameter(Mandatory = $true)][string]$DirectiveGitBlob,
        [Parameter(Mandatory = $true)][string]$TempRootPath,
        [Parameter(Mandatory = $true)][bool]$SkipVerify
    )
    $Setup = Get-DirectiveFenceBody -Text $DirectiveText `
        -HeadingPrefix '### 5.2 Exact PowerShell setup' -Language 'powershell'

    $Substitutions = @(
        @('<ENTRY_OR_RESUME>', $EntryMode),
        @('<DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256>', $CapsuleToken),
        @('<DISPATCH_EXACT_DIRECTIVE_RAW_SHA256>', $DirectiveRawSha256),
        @('<DISPATCH_EXACT_DIRECTIVE_GIT_BLOB>', $DirectiveGitBlob)
    )
    foreach ($Pair in $Substitutions) {
        $Placeholder = [string]$Pair[0]
        $Value = [string]$Pair[1]
        if (-not $Setup.Contains($Placeholder)) {
            throw (New-ControllerFailure `
                -Message "setup placeholder absent: $Placeholder" `
                -InputInvalid $true)
        }
        $Setup = $Setup.Replace($Placeholder, $Value)
    }
    if ($TempRootPath -ne $FrozenTempRoot) {
        # Rehearsal redirection: the frozen literal is replaced so the whole
        # driver can run against a scratch root.
        if (-not $Setup.Contains($FrozenTempRoot)) {
            throw (New-ControllerFailure `
                -Message 'setup temp root literal absent' -InputInvalid $true)
        }
        $Setup = $Setup.Replace($FrozenTempRoot, $TempRootPath)
    }
    if ($SkipVerify) {
        $Setup = $Setup.Replace(
            "if (`$ProcessEntryMode -eq 'ENTRY') {",
            "if (`$false) {"
        )
    }
    if ($Setup.Contains('<DISPATCH_') -or $Setup.Contains('<ENTRY_OR_')) {
        throw (New-ControllerFailure `
            -Message 'unsubstituted placeholder remains in setup' `
            -InputInvalid $true)
    }
    return $Setup
}

# ---------------------------------------------------------------------------
# Appendix materialization (section 2.4)
# ---------------------------------------------------------------------------

function Write-AppendixFile {
    param(
        [Parameter(Mandatory = $true)][string]$Body,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256
    )
    $ActualSourceSha = Get-Sha256OfString -Value $Body
    if ($ActualSourceSha -ne $ExpectedSha256) {
        throw (New-ControllerFailure `
            -Message ("appendix source SHA mismatch for " + $Path + ": " +
                $ActualSourceSha) `
            -InputInvalid $true)
    }
    if (Test-Path -LiteralPath $Path) {
        throw (New-ControllerFailure `
            -Message "appendix target already exists: $Path" `
            -InputInvalid $true)
    }
    $Bytes = $ControllerUtf8NoBom.GetBytes($Body)
    $Stream = [System.IO.File]::Open(
        $Path,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $Stream.Write($Bytes, 0, $Bytes.Length)
        $Stream.Flush($true)
    } finally {
        $Stream.Dispose()
    }
    $WrittenSha = Get-Sha256OfFile -Path $Path
    if ($WrittenSha -ne $ExpectedSha256) {
        throw (New-ControllerFailure `
            -Message "appendix file SHA mismatch after write: $Path" `
            -InputInvalid $false)
    }
    return $WrittenSha
}

# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------

function Initialize-ControllerContext {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$RepoInput,
        [Parameter(Mandatory = $true)][AllowEmptyString()]
        [string]$RehearsalRootInput
    )
    $RepoPath = if ([string]::IsNullOrEmpty($RepoInput)) {
        (Resolve-Path -LiteralPath '.').Path
    } else {
        (Resolve-Path -LiteralPath $RepoInput).Path
    }
    $DirectivePath = Join-Path $RepoPath $DirectiveRelativePath
    $DirectiveText = Get-DirectiveText -Path $DirectivePath
    $TempRootPath = if ([string]::IsNullOrEmpty($RehearsalRootInput)) {
        $FrozenTempRoot
    } else {
        Join-Path $RehearsalRootInput 'temp-root'
    }
    $EvidenceRoot = if ([string]::IsNullOrEmpty($RehearsalRootInput)) {
        Join-Path $RepoPath (
            'reports\canonical_shell_rc_provenance'
        )
    } else {
        Join-Path $RehearsalRootInput 'evidence'
    }
    return [pscustomobject]@{
        RepoPath = $RepoPath
        DirectivePath = $DirectivePath
        DirectiveText = $DirectiveText
        DirectiveRawSha256 = Get-Sha256OfFile -Path $DirectivePath
        PythonPath = (Resolve-Path -LiteralPath (
            Join-Path $RepoPath 'venv\Scripts\python.exe'
        )).Path
        WorkbookPath = (Resolve-Path -LiteralPath (
            Join-Path $RepoPath 'tc_samples\TC_1.xlsx'
        )).Path
        TempRootPath = $TempRootPath
        EvidenceRoot = $EvidenceRoot
        EvidenceRunDir = Join-Path $EvidenceRoot 'RB-20260728-shellrc-p0p1'
        IsRehearsal = -not [string]::IsNullOrEmpty($RehearsalRootInput)
    }
}

# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------

function Invoke-PrepareMode {
    param([Parameter(Mandatory = $true)][object]$Context)

    $DirectiveBlob = (Invoke-ControllerGit -RepoPath $Context.RepoPath `
        -ArgumentList @(
            'hash-object', '--no-filters', '--', $DirectiveRelativePath
        )).StandardOutput.Trim()

    $PreflightObserved = Assert-HostPreflightItems `
        -RepoPath $Context.RepoPath `
        -DirectiveText $Context.DirectiveText `
        -WorkbookPath $Context.WorkbookPath `
        -PythonPath $Context.PythonPath `
        -TempRootPath $Context.TempRootPath `
        -EvidenceRunDir $Context.EvidenceRunDir

    $SetupSource = Import-DirectiveSetup `
        -DirectiveText $Context.DirectiveText `
        -EntryMode 'ENTRY' `
        -CapsuleToken $CapsuleSha256 `
        -DirectiveRawSha256 $Context.DirectiveRawSha256 `
        -DirectiveGitBlob $DirectiveBlob `
        -TempRootPath $Context.TempRootPath `
        -SkipVerify ([bool]$RehearsalSkipVerify)

    # Running the directive's own setup performs preflight items 1-3, 11
    # and 12 (capsule identity, verifier, TTL, module-route fs gate).
    . ([scriptblock]::Create($SetupSource))

    if ($RehearsalSkipVerify) {
        $script:DispatchCapsule = (
            [System.IO.File]::ReadAllText(
                (Join-Path 'C:\tmp\tc-runner-dispatch-capsules' (
                    $CapsuleSha256 + '.json'
                )),
                $ControllerUtf8NoBom
            ) | ConvertFrom-Json
        )
        $script:CapsuleVerifyExit = 0
    }

    # First writes begin here; every gate above was read-only.
    $null = New-Item -ItemType Directory -Path $Context.TempRootPath
    if (-not (Test-Path -LiteralPath $Context.EvidenceRoot)) {
        $null = New-Item -ItemType Directory -Path $Context.EvidenceRoot
    }
    $null = New-Item -ItemType Directory -Path $Context.EvidenceRunDir

    $LedgerSource = Get-DirectiveFenceBody -Text $Context.DirectiveText `
        -HeadingPrefix '### 2.5 Actual phase ledger' -Language 'powershell'
    . ([scriptblock]::Create($LedgerSource))

    $HostRowSource = Get-DirectiveFenceBody -Text $Context.DirectiveText `
        -HeadingPrefix '## 3. Entry Preflight' -Language 'powershell'
    . ([scriptblock]::Create($HostRowSource))

    $AppendixPins = Get-AssemblerAppendixPins -Text $Context.DirectiveText
    $AppendixBBody = Get-DirectiveFenceBody -Text $Context.DirectiveText `
        -HeadingPrefix '## Appendix B ' -Language 'python'
    $AppendixCBody = Get-DirectiveFenceBody -Text $Context.DirectiveText `
        -HeadingPrefix '## Appendix C ' -Language 'python'

    $AppendixBSha = $null
    $AppendixCSha = $null
    try {
        $AppendixBSha = Write-AppendixFile -Body $AppendixBBody `
            -Path (Join-Path $Context.TempRootPath 'analyze_provenance.py') `
            -ExpectedSha256 ([string]$AppendixPins['b'])
        $AppendixCSha = Write-AppendixFile -Body $AppendixCBody `
            -Path (Join-Path $Context.TempRootPath 'assemble_evidence.py') `
            -ExpectedSha256 ([string]$AppendixPins['c'])
    } catch {
        $Failure = $_.Exception
        Add-PhaseRecord ([ordered]@{
            phase = 'APPENDIX_MATERIALIZATION'
            status = 'FAILED'
            tool = 'PowerShell'
            cwd = $Repo
            argv = $null
            tool_input_sha256 = $null
            exit = $null
            observed = [ordered]@{}
            error_class = $Failure.GetType().Name
            error_message = $Failure.Message
        })
        throw $Failure
    }

    $MaterializationRowSource = Get-DirectiveFenceBody `
        -Text $Context.DirectiveText `
        -HeadingPrefix '### 2.4 Appendix byte materialization' `
        -Language 'powershell'
    . ([scriptblock]::Create($MaterializationRowSource))

    $AppendixASha = Get-Sha256OfString -Value (
        Get-DirectiveFenceBody -Text $Context.DirectiveText `
            -HeadingPrefix '## Appendix A ' -Language 'javascript'
    )
    $AppendixRSha = Get-Sha256OfString -Value (
        Get-DirectiveFenceBody -Text $Context.DirectiveText `
            -HeadingPrefix '## Appendix R ' -Language 'javascript'
    )

    $Handoff = [ordered]@{
        mode = 'prepare'
        status = 'COMPLETED'
        temp_root = $Context.TempRootPath
        evidence_run_dir = $Context.EvidenceRunDir
        capsule_sha256 = $CapsuleSha256
        directive_raw_sha256 = $Context.DirectiveRawSha256
        directive_git_blob = $DirectiveBlob
        appendix_a_source_sha256 = $AppendixASha
        appendix_b_source_sha256 = $AppendixBSha
        appendix_c_source_sha256 = $AppendixCSha
        appendix_r_source_sha256 = $AppendixRSha
        module_root_path = [string](
            $DispatchCapsule.module_roots[0].root_path
        )
        preflight = $PreflightObserved
        next = @(
            'submit Appendix R to node_repl.js (timeout_ms >= 300000)',
            ('on import failure call js_add_node_module_dir once with ' +
                'module_root_path then resubmit Appendix R'),
            'submit Appendix A to node_repl.js (timeout_ms >= 300000)',
            'run this controller again with -Mode resume'
        )
    }
    [Console]::Out.WriteLine(($Handoff | ConvertTo-Json -Depth 8))
    return 0
}

# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------

function Invoke-ResumeMode {
    param([Parameter(Mandatory = $true)][object]$Context)

    $DirectiveBlob = (Invoke-ControllerGit -RepoPath $Context.RepoPath `
        -ArgumentList @(
            'hash-object', '--no-filters', '--', $DirectiveRelativePath
        )).StandardOutput.Trim()

    $SetupSource = Import-DirectiveSetup `
        -DirectiveText $Context.DirectiveText `
        -EntryMode 'RESUME' `
        -CapsuleToken $CapsuleSha256 `
        -DirectiveRawSha256 $Context.DirectiveRawSha256 `
        -DirectiveGitBlob $DirectiveBlob `
        -TempRootPath $Context.TempRootPath `
        -SkipVerify $false
    . ([scriptblock]::Create($SetupSource))

    $LedgerSource = Get-DirectiveFenceBody -Text $Context.DirectiveText `
        -HeadingPrefix '### 2.5 Actual phase ledger' -Language 'powershell'
    . ([scriptblock]::Create($LedgerSource))

    $Status = 'measured'
    $LastPhase = 'ANALYZE'
    $ErrorClass = ''
    $ErrorMessage = ''

    try {
        $P0GateSource = Get-DirectiveFenceBody -Text $Context.DirectiveText `
            -HeadingPrefix '### 4.3 P0 output rows' -Language 'powershell'
        . ([scriptblock]::Create($P0GateSource))

        $P0Row = $P0SuccessRecord
        $P0Reconciled = [bool]$P0Row.observed.reconciled
        $P0IdentityOk = (
            [bool]$P0Row.observed.input_identity_valid -and
            [bool]$P0Row.observed.producer_input_identity_valid
        )
        if (-not $P0IdentityOk -or -not $P0Reconciled) {
            $LastPhase = 'P0_ARTIFACT_CAPTURE'
        } else {
            $DrySource = Get-DirectiveFenceBody -Text $Context.DirectiveText `
                -HeadingPrefix '### 5.3 Exact dry-run argv' `
                -Language 'powershell'
            . ([scriptblock]::Create($DrySource))
            Assert-DryRunTotals -TempRootPath $Context.TempRootPath

            $ExportSource = Get-DirectiveFenceBody `
                -Text $Context.DirectiveText `
                -HeadingPrefix '### 5.4 Exact isolated-export argv' `
                -Language 'powershell'
            . ([scriptblock]::Create($ExportSource))

            $AnalyzeSource = Get-DirectiveFenceBody `
                -Text $Context.DirectiveText `
                -HeadingPrefix '### 5.7 Exact analysis-only argv' `
                -Language 'powershell'
            . ([scriptblock]::Create($AnalyzeSource))
            $LastPhase = 'ANALYZE'
        }
    } catch {
        $Failure = $_.Exception
        $Status = 'infra_failure'
        $ErrorClass = $Failure.GetType().Name
        $ErrorMessage = $Failure.Message
        $LastPhase = Get-LastLedgerPhase -TempRootPath $Context.TempRootPath
    }

    $AssembleSource = Get-DirectiveFenceBody -Text $Context.DirectiveText `
        -HeadingPrefix '### 6.3 Exact evidence assembler invocation' `
        -Language 'powershell'
    $AssembleSource = $AssembleSource.Replace(
        '<DISPATCH_EXACT_DIRECTIVE_RAW_SHA256>', $Context.DirectiveRawSha256
    ).Replace(
        '<DISPATCH_EXACT_DIRECTIVE_GIT_BLOB>', $DirectiveBlob
    ).Replace(
        '<DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256>', $CapsuleSha256
    )
    if ($Context.IsRehearsal) {
        # Appendix C resolves the repo evidence path from frozen literals,
        # so a rehearsal must not invoke it. The argv is still built by the
        # directive's own fence and reported for inspection.
        $AssembleSource = $AssembleSource.Replace(
            '& $Python @AssembleArgs',
            '[Console]::Out.WriteLine("REHEARSAL_ASSEMBLE_ARGV " + ' +
                '(@($AssembleArgs) -join " "))'
        ).Replace(
            '$CampaignExit = $LASTEXITCODE',
            '$CampaignExit = 0'
        )
    }
    . ([scriptblock]::Create($AssembleSource))
    return [int]$CampaignExit
}

function Assert-DryRunTotals {
    param([Parameter(Mandatory = $true)][string]$TempRootPath)
    foreach ($Sheet in @('SS-TC-0', 'SS-TC-1')) {
        $LogPath = Join-Path $TempRootPath (
            'dry-run-' + $Sheet + '.combined.txt'
        )
        $Text = [System.IO.File]::ReadAllText($LogPath, $ControllerUtf8NoBom)
        $Match = [regex]::Match($Text, 'Total:\s*(\d+)\s*TCs')
        if (-not $Match.Success) {
            throw (New-ControllerFailure `
                -Message "dry-run total not found for $Sheet" `
                -InputInvalid $false)
        }
        if ([int]$Match.Groups[1].Value -le 0) {
            throw (New-ControllerFailure `
                -Message "dry-run total is not positive for $Sheet" `
                -InputInvalid $false)
        }
    }
}

function Get-LastLedgerPhase {
    param([Parameter(Mandatory = $true)][string]$TempRootPath)
    $LedgerPath = Join-Path $TempRootPath 'operation_log.ndjson'
    if (-not (Test-Path -LiteralPath $LedgerPath -PathType Leaf)) {
        return 'HOST_PREFLIGHT'
    }
    $Rows = @(
        [System.IO.File]::ReadAllLines($LedgerPath, $ControllerUtf8NoBom) |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { $_ | ConvertFrom-Json }
    )
    if ($Rows.Count -eq 0) { return 'HOST_PREFLIGHT' }
    return [string]$Rows[$Rows.Count - 1].phase
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

function Invoke-SelfTestMode {
    # Runtime smoke of every controller helper that touches the .NET or
    # process surface. Static parsing cannot catch APIs that are absent on
    # .NET Framework (for example ProcessStartInfo.ArgumentList), so each
    # helper is actually executed here.
    param([Parameter(Mandatory = $true)][object]$Context)
    $Failures = New-Object System.Collections.Generic.List[string]

    function Add-SelfTest {
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
        [Console]::Out.WriteLine($Line)
        if (-not $Passed) { $script:SelfTestFailures.Add($Name) }
    }
    $script:SelfTestFailures = $Failures

    $Quoted = ConvertTo-ProcessArgumentString -ArgumentList @(
        'plain', 'with space', 'with"quote', 'C:\path\', ''
    )
    Add-SelfTest -Name 'S1 argument quoting' `
        -Passed ($Quoted -ceq 'plain "with space" "with\"quote" C:\path\ ""') `
        -Detail $Quoted

    $GitVersion = Invoke-ControllerProcess -FilePath 'git' `
        -ArgumentList @('--version') -WorkingDirectory $Context.RepoPath
    Add-SelfTest -Name 'S2 process helper runs' `
        -Passed ($GitVersion.ExitCode -eq 0 -and
            $GitVersion.StandardOutput.StartsWith('git version')) `
        -Detail $GitVersion.StandardOutput.Trim()

    $Head = Invoke-ControllerGit -RepoPath $Context.RepoPath `
        -ArgumentList @('rev-parse', 'HEAD')
    Add-SelfTest -Name 'S3 git helper runs' `
        -Passed ($Head.StandardOutput.Trim() -match '^[0-9a-f]{40}$') `
        -Detail $Head.StandardOutput.Trim()

    $Dirty = Invoke-ControllerGit -RepoPath $Context.RepoPath `
        -ArgumentList @('diff', '--quiet') -AllowedExitCodes @(0, 1)
    Add-SelfTest -Name 'S4 git allowed-exit handling' `
        -Passed ($Dirty.ExitCode -in @(0, 1)) `
        -Detail ('exit=' + $Dirty.ExitCode)

    $Mtime = Get-WorkbookMtimeNs -Path $Context.WorkbookPath
    Add-SelfTest -Name 'S5 workbook mtime probe' `
        -Passed ($Mtime -match '^\d+$') -Detail $Mtime

    $Actors = Get-DirectiveTablePairs -Text $Context.DirectiveText `
        -HeadingPrefix '### 1.3 Producer actor set'
    Add-SelfTest -Name 'S6 actor table parse' `
        -Passed ($Actors.Count -eq 14) -Detail ('count=' + $Actors.Count)

    $Audit = Get-FrozenAuditPairs -Text $Context.DirectiveText
    Add-SelfTest -Name 'S7 frozen audit parse' `
        -Passed ($Audit.Count -eq 4) -Detail ('count=' + $Audit.Count)

    $Pins = Get-AssemblerAppendixPins -Text $Context.DirectiveText
    Add-SelfTest -Name 'S8 assembler pin parse' `
        -Passed ($Pins.Count -eq 3) -Detail ('count=' + $Pins.Count)

    $Toolchain = Get-ToolchainObservation -RepoPath $Context.RepoPath `
        -PythonPath $Context.PythonPath -DirectiveText $Context.DirectiveText
    Add-SelfTest -Name 'S9 toolchain probe matches frozen object' `
        -Passed ($Toolchain.Count -eq 11) `
        -Detail ('python=' + [string]$Toolchain['python'] +
            ' node=' + [string]$Toolchain['node'])

    $Setup = Import-DirectiveSetup -DirectiveText $Context.DirectiveText `
        -EntryMode 'RESUME' -CapsuleToken ('0' * 64) `
        -DirectiveRawSha256 ('1' * 64) -DirectiveGitBlob ('2' * 40) `
        -TempRootPath $Context.TempRootPath -SkipVerify $false
    Add-SelfTest -Name 'S10 setup substitution' `
        -Passed ($Setup.Contains("ProcessEntryMode = 'RESUME'") -and
            -not $Setup.Contains('<DISPATCH_')) `
        -Detail ('chars=' + $Setup.Length)

    [Console]::Out.WriteLine('')
    if ($Failures.Count -eq 0) {
        [Console]::Out.WriteLine('CONTROLLER SELFTEST GREEN')
        return 0
    }
    [Console]::Out.WriteLine(
        'CONTROLLER SELFTEST FAILED: ' + ($Failures -join ',')
    )
    return 1
}

try {
    $Context = Initialize-ControllerContext -RepoInput $RepoRoot `
        -RehearsalRootInput $RehearsalRoot
    if ($Mode -eq 'selftest') {
        exit (Invoke-SelfTestMode -Context $Context)
    }
    if ([string]::IsNullOrEmpty($CapsuleSha256)) {
        throw (New-ControllerFailure `
            -Message 'CapsuleSha256 is required for prepare/resume' `
            -InputInvalid $true)
    }
    if ($Mode -eq 'prepare') {
        exit (Invoke-PrepareMode -Context $Context)
    }
    exit (Invoke-ResumeMode -Context $Context)
} catch {
    $Failure = $_.Exception
    [Console]::Error.WriteLine(
        $Failure.GetType().Name + ': ' + $Failure.Message
    )
    exit (Get-ControllerExitCode -Exception $Failure)
}

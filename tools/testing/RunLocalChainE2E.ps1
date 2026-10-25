#Requires -Version 7.0
<#
.SYNOPSIS
  One reproducible command for the LocalChainEndToEndTest role.

.DESCRIPTION
  Runs the real development-host negatives and the health probes, records every
  child's raw stdout/stderr bytes and exit code, then runs the positive end-to-end
  chain only when a real Owner binding already exists.

  The script never confirms an Owner action, never patches `isatty`, never edits
  product source and never invokes a model. When the Owner binding is absent it
  prints the exact human TTY `owner-init` command and records the positive chain as
  NOT_EXECUTED with that reason.

  It only writes below -EvidenceRoot (default: the test role's own process
  directory). The instance ACL is verified but not modified unless -RepairAcl is
  given; the same applies to registration freshness (it reports, it never rebuilds).

.EXAMPLE
  pwsh -NoProfile -File ./RunLocalChainE2E.ps1

.EXAMPLE
  # Gate mode: exit 2 when the Owner binding (and therefore the positive chain)
  # does not exist, so a green run always means the full chain really ran.
  pwsh -NoProfile -File ./RunLocalChainE2E.ps1 -RequirePositive
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = 'G:/开发测试/Projects/VideoCreator',
    [string]$InstallationRoot = 'G:/开发测试/Codex/VideoCreatorImplementation/Integration/LocalInstallationRegistrationBuild',
    [string]$EvidenceRoot = 'G:/开发测试/Codex/VideoCreatorImplementation/Test/LocalChainEndToEnd/Evidence',
    [int]$TimeoutSeconds = 1800,
    [switch]$RequirePositive,
    [switch]$RepairAcl
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Python = Join-Path $RepoRoot '.venv/Scripts/python.exe'
$EngineSource = Join-Path $RepoRoot 'services/engine/src'
$Probes = Join-Path $RepoRoot 'tools/testing/local_chain_probes.py'
$Tests = Join-Path $RepoRoot 'tests/development'
$InstanceDir = Join-Path $InstallationRoot 'Instance/ChainInstance'
$Registration = Join-Path $InstallationRoot 'Registration.json'

$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$RunDir = Join-Path $EvidenceRoot "$Stamp-e2e"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$env:PYTHONPATH = $EngineSource
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:VIDEO_CREATOR_LOCAL_INSTALLATION = $InstallationRoot
$env:VIDEO_CREATOR_LOCAL_INSTANCE = $InstanceDir
$env:VIDEO_CREATOR_LOCAL_CHAIN_EVIDENCE = $RunDir

$Summary = [ordered]@{
    started_at = (Get-Date).ToUniversalTime().ToString('o')
    stamp = $Stamp
    repo = $RepoRoot
    installation = $InstallationRoot
    instance = $InstanceDir
    registration = $Registration
    evidence = $RunDir
    python = $Python
    commands = @()
    versions = [ordered]@{}
    shas = [ordered]@{}
    owner_state = $null
    source_status = $null
    not_executed = @()
    results = [ordered]@{}
    ok = $false
}

function Write-Step([string]$Text) {
    Write-Host ''
    Write-Host "== $Text" -ForegroundColor Cyan
}

function Quote-Arg([string]$Value) {
    if ($Value -match '\s') { return '"' + $Value + '"' }
    return $Value
}

function Invoke-Recorded {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [int]$Timeout = 600
    )
    $stdout = Join-Path $RunDir "$Name.stdout.bin"
    $stderr = Join-Path $RunDir "$Name.stderr.bin"
    $quoted = @($Arguments | ForEach-Object { Quote-Arg $_ })
    $process = Start-Process -FilePath $FilePath -ArgumentList $quoted -PassThru -NoNewWindow `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $finished = $process.WaitForExit($Timeout * 1000)
    if (-not $finished) {
        try { $process.Kill($true) } catch { }
        $process.WaitForExit(30000) | Out-Null
    }
    $exit = if ($finished) { $process.ExitCode } else { -1 }
    $entry = [ordered]@{
        name = $Name
        argv = @($FilePath) + $Arguments
        exit = $exit
        timeout = (-not $finished)
        started_at = (Get-Date).ToUniversalTime().ToString('o')
        stdout = $stdout
        stderr = $stderr
        stdout_bytes = (Get-Item $stdout).Length
        stderr_bytes = (Get-Item $stderr).Length
    }
    $Summary.commands += $entry
    $code = $null
    if ((Get-Item $stderr).Length -gt 0) {
        $text = [System.IO.File]::ReadAllText($stderr, [System.Text.Encoding]::UTF8)
        foreach ($line in ($text -split "`n")) {
            if (-not $line.TrimStart().StartsWith('{')) { continue }
            try { $code = ($line | ConvertFrom-Json).code } catch { }
        }
    }
    return [pscustomobject]@{ exit = $exit; stdout = $stdout; stderr = $stderr; code = $code }
}

function Write-Utf8Lf([string]$Path, [string]$Text) {
    $normalized = ($Text -replace "`r`n", "`n") -replace "`r", "`n"
    [System.IO.File]::WriteAllText($Path, $normalized, [System.Text.UTF8Encoding]::new($false))
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Invoke-Probe {
    param([string]$Name, [string[]]$Arguments)
    $result = Invoke-Recorded -Name $Name -FilePath $Python -Arguments (@($Probes, '--repo', $RepoRoot) + $Arguments) -Timeout 300
    $json = $null
    if (Test-Path -LiteralPath $result.stdout) {
        $text = [System.IO.File]::ReadAllText($result.stdout, [System.Text.Encoding]::UTF8)
        foreach ($line in ($text -split "`n")) {
            if (-not $line.TrimStart().StartsWith('{')) { continue }
            try { $json = $line | ConvertFrom-Json } catch { }
        }
    }
    return [pscustomobject]@{ exit = $result.exit; json = $json; argv = $Arguments }
}

function Get-JUnitCounts([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        [xml]$xml = Get-Content -LiteralPath $Path -Raw
        $root = $xml.DocumentElement
        $suite = if ($root.Name -eq 'testsuite') { $root } else { $root.SelectSingleNode('testsuite') }
        if ($null -eq $suite) { return $null }
        return [ordered]@{
            tests = [int]$suite.tests
            failures = [int]$suite.failures
            errors = [int]$suite.errors
            skipped = [int]$suite.skipped
            time = [string]$suite.time
        }
    }
    catch { return $null }
}

function Invoke-Pytest {
    param([string]$Name, [string[]]$Targets)
    $junit = Join-Path $RunDir "$Name.xml"
    $arguments = @('-m', 'pytest') + $Targets + @('-q', '-rs', '-p', 'no:cacheprovider', "--junitxml=$junit")
    $result = Invoke-Recorded -Name $Name -FilePath $Python -Arguments $arguments -Timeout $TimeoutSeconds
    $counts = Get-JUnitCounts $junit
    $codes = [ordered]@{}
    $nested = @(Get-ChildItem -LiteralPath $RunDir -Directory | Where-Object { $_.Name -like '*-pytest-*' } |
        Sort-Object Name | Select-Object -Last 1)
    if ($nested.Count -gt 0) {
        foreach ($stderrFile in (Get-ChildItem -LiteralPath $nested[0].FullName -Filter '*.stderr.bin')) {
            if ($stderrFile.Length -eq 0) { continue }
            $text = [System.IO.File]::ReadAllText($stderrFile.FullName, [System.Text.Encoding]::UTF8)
            $code = $null
            foreach ($line in ($text -split "`n")) {
                if (-not $line.TrimStart().StartsWith('{')) { continue }
                try { $code = ($line | ConvertFrom-Json).code } catch { }
            }
            if ($code) { $codes[$stderrFile.BaseName -replace '\.stderr$', ''] = $code }
        }
    }
    $Summary.results[$Name] = [ordered]@{
        exit = $result.exit
        junit = $junit
        junit_sha256 = (Get-Sha256 $junit)
        counts = $counts
        refusal_codes = $codes
    }
    return [pscustomobject]@{ exit = $result.exit; junit = $junit; counts = $counts }
}

try {
    Write-Step '0/6 preconditions'
    foreach ($required in @($Python, $Probes, $Registration, (Join-Path $InstallationRoot 'Package/Media/FFmpeg/bin/ffmpeg.exe'),
                           (Join-Path $InstallationRoot 'Package/Media/FFmpeg/bin/ffprobe.exe'), $Tests)) {
        if (-not (Test-Path -LiteralPath $required)) { throw "required path missing: $required" }
    }
    if (-not (Test-Path -LiteralPath $InstanceDir)) { throw "chain instance missing: $InstanceDir" }
    Write-Host "evidence: $RunDir"

    Write-Step '1/6 environment and artifact facts'
    $pythonVersion = Invoke-Recorded -Name 'version-python' -FilePath $Python -Arguments @('-VV')
    $ffmpegVersion = Invoke-Recorded -Name 'version-ffmpeg' -FilePath (Join-Path $InstallationRoot 'Package/Media/FFmpeg/bin/ffmpeg.exe') -Arguments @('-version')
    $ffprobeVersion = Invoke-Recorded -Name 'version-ffprobe' -FilePath (Join-Path $InstallationRoot 'Package/Media/FFmpeg/bin/ffprobe.exe') -Arguments @('-version')
    $gitHead = Invoke-Recorded -Name 'git-head' -FilePath 'git' -Arguments @('-C', $RepoRoot, 'rev-parse', 'HEAD')
    $gitStatus = Invoke-Recorded -Name 'git-status' -FilePath 'git' -Arguments @('-C', $RepoRoot, 'status', '--porcelain')
    $acl = Invoke-Recorded -Name 'instance-acl' -FilePath 'icacls' -Arguments @($InstanceDir)

    $read = { param($path) [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8) }
    $Summary.versions['python'] = (((& $read $pythonVersion.stdout) -split "`n")[0]).Trim()
    $Summary.versions['ffmpeg'] = (((& $read $ffmpegVersion.stdout) -split "`n")[0]).Trim()
    $Summary.versions['ffprobe'] = (((& $read $ffprobeVersion.stdout) -split "`n")[0]).Trim()
    $Summary.shas['python_exit'] = $pythonVersion.exit
    $Summary.shas['ffmpeg_exit'] = $ffmpegVersion.exit
    $Summary.shas['ffprobe_exit'] = $ffprobeVersion.exit
    $Summary.shas['git_head'] = ((& $read $gitHead.stdout).Trim())
    $Summary.shas['git_status_porcelain'] = ((& $read $gitStatus.stdout).Trim())
    $Summary.shas['registration'] = Get-Sha256 $Registration
    $Summary.shas['registration_bytes'] = (Get-Item -LiteralPath $Registration).Length
    $Summary.shas['runtime_manifest'] = Get-Sha256 (Join-Path $InstallationRoot 'Package/RuntimeFileManifest.json')
    $Summary.shas['local_material_resources'] = Get-Sha256 (Join-Path $InstallationRoot 'Package/LocalMaterialResources.json')
    $Summary.shas['ffmpeg'] = Get-Sha256 (Join-Path $InstallationRoot 'Package/Media/FFmpeg/bin/ffmpeg.exe')
    $Summary.shas['ffprobe'] = Get-Sha256 (Join-Path $InstallationRoot 'Package/Media/FFmpeg/bin/ffprobe.exe')
    Write-Host "python:  $($Summary.versions['python'])"
    Write-Host "ffmpeg:  $($Summary.versions['ffmpeg'])"
    Write-Host "ffprobe: $($Summary.versions['ffprobe'])"
    Write-Host "HEAD:    $($Summary.shas['git_head'])"
    Write-Host "registration sha256: $($Summary.shas['registration'])"

    Write-Step '2/6 Owner binding and registration freshness (read-only)'
    $ownerProbe = Invoke-Probe -Name 'owner-state' -Arguments @('owner-state', '--data-dir', $InstanceDir,
        '--project-id', ((Get-Content -LiteralPath $Registration -Raw | ConvertFrom-Json).local_registration.rights_declaration.project_ids[0]))
    if ($null -eq $ownerProbe.json) { throw 'owner-state probe produced no JSON' }
    $Summary.owner_state = $ownerProbe.json
    $sourceProbe = Invoke-Probe -Name 'source-status' -Arguments @('source-status', '--registration', $Registration)
    if ($null -eq $sourceProbe.json) { throw 'source-status probe produced no JSON' }
    $Summary.source_status = $sourceProbe.json
    Write-Host "owner_initialized=$($ownerProbe.json.owner_initialized) owner_active=$($ownerProbe.json.owner_active) code=$($ownerProbe.json.error_code)"
    Write-Host "registration fresh=$($sourceProbe.json.ok) changed=$(@($sourceProbe.json.changed_files).Count)"

    if (-not $sourceProbe.json.ok) {
        $Summary.not_executed += [ordered]@{
            case = 'tests/development'
            reason = 'registration is stale against the current checkout'
            fix = "pwsh -NoProfile -File '$InstallationRoot/build_local_registration.py'"
        }
        $changed = @($sourceProbe.json.changed_files) -join ','
        $staleMessage = 'The frozen registration does not match the current engine bytes '
        $staleMessage += "(declared=$($sourceProbe.json.declared_count) current=$($sourceProbe.json.current_count) changed=$changed). "
        $staleMessage += 'Regenerate it first; no dev-host case is meaningful against stale bytes.'
        throw $staleMessage
    }

    if ($ownerProbe.json.error_code -eq 'owner_directory_denied') {
        $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        if ($RepairAcl) {
            Write-Host 'repairing the instance ACL to the current SID and SYSTEM' -ForegroundColor Yellow
            & icacls $InstanceDir /inheritance:r | Out-Null
            & icacls $InstanceDir /grant:r "*${sid}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'icacls failed to restrict the instance directory' }
        }
        else {
            $aclMessage = "The Owner store directory is writable by another principal ($($ownerProbe.json.code)). "
            $aclMessage += 'Re-run with -RepairAcl, or apply: icacls "' + $InstanceDir + '" /inheritance:r; icacls "'
            $aclMessage += $InstanceDir + '" /grant:r "*' + $sid + ':(OI)(CI)F" "*S-1-5-18:(OI)(CI)F"'
            throw $aclMessage
        }
    }

    Write-Step '3/6 real refusals + health visibility'
    $negatives = Invoke-Pytest -Name 'pytest-negatives' -Targets @(
        (Join-Path $Tests 'test_development_host_negatives.py'),
        (Join-Path $Tests 'test_development_host_health.py'))
    Write-Host "negatives exit=$($negatives.exit) counts=$(($negatives.counts | ConvertTo-Json -Compress))"

    Write-Step '4/6 positive local chain (Owner binding required)'
    $ownerActive = [bool]$ownerProbe.json.owner_active
    if ($ownerActive) {
        $positive = Invoke-Pytest -Name 'pytest-local-chain' -Targets @((Join-Path $Tests 'test_local_chain_end_to_end.py'))
        Write-Host "positive exit=$($positive.exit) counts=$(($positive.counts | ConvertTo-Json -Compress))"
    }
    else {
        $instanceId = $ownerProbe.json.instance_id
        $expires = (Get-Date).ToUniversalTime().AddDays(6).ToString('yyyy-MM-ddTHH:mm:ssZ')
        $ownerCommand = @"
`$env:PYTHONPATH = '$EngineSource'
& '$Python' -m video_creator.cli.main owner-init ``
  --data-dir '$InstanceDir' ``
  --action initialize --action-key 'chain-owner-init-1' ``
  --owner-subject 'local-user' ``
  --project-id '$((Get-Content -LiteralPath $Registration -Raw | ConvertFrom-Json).local_registration.rights_declaration.project_ids[0])' ``
  --expires-at '$expires'
"@
        Write-Utf8Lf -Path (Join-Path $RunDir 'owner-init-command.ps1') -Text $ownerCommand
        Write-Host 'The real Owner binding is absent. One human TTY action is required; this script never fakes it:' -ForegroundColor Yellow
        Write-Host $ownerCommand -ForegroundColor Green
        $Summary.not_executed += [ordered]@{
            case = 'tests/development/test_local_chain_end_to_end.py::test_local_chain_produces_a_verifiable_0_4_bundle'
            reason = "no real Owner binding (owner_initialized=$($ownerProbe.json.owner_initialized), owner_active=$($ownerProbe.json.owner_active), code=$($ownerProbe.json.error_code))"
            fix = 'run owner-init-command.ps1 in a real interactive terminal, then re-run this script'
        }
        $Summary.results['pytest-local-chain'] = [ordered]@{ exit = $null; not_executed = $true; counts = $null }
    }

    Write-Step '5/6 evidence inventory'
    $inventory = Get-ChildItem -LiteralPath $RunDir -File | ForEach-Object {
        [ordered]@{ name = $_.Name; bytes = $_.Length; sha256 = (Get-Sha256 $_.FullName) }
    }
    $Summary.shas['evidence_files'] = @($inventory).Count
    Write-Utf8Lf -Path (Join-Path $RunDir 'EvidenceInventory.json') -Text ($inventory | ConvertTo-Json -Depth 5)

    Write-Step '6/6 summary'
    $executedFailure = $false
    foreach ($name in $Summary.results.Keys) {
        $entry = $Summary.results[$name]
        if ($null -ne $entry.exit -and $entry.exit -ne 0) { $executedFailure = $true }
        if ($entry.counts -and ($entry.counts.failures -gt 0 -or $entry.counts.errors -gt 0)) { $executedFailure = $true }
    }
    $Summary.ok = -not $executedFailure
    $Summary.finished_at = (Get-Date).ToUniversalTime().ToString('o')
    Write-Utf8Lf -Path (Join-Path $RunDir 'RunSummary.json') -Text ($Summary | ConvertTo-Json -Depth 12)
    Write-Host "summary: $(Join-Path $RunDir 'RunSummary.json')"
    Write-Host "executed failures: $executedFailure; positive executed: $ownerActive"

    if ($executedFailure) { exit 1 }
    if ($RequirePositive -and -not $ownerActive) {
        Write-Host 'RequirePositive was set but the real Owner binding is absent; the positive chain did not run.' -ForegroundColor Red
        exit 2
    }
    exit 0
}
catch {
    $Summary.error = "$_"
    $Summary.ok = $false
    $Summary.finished_at = (Get-Date).ToUniversalTime().ToString('o')
    Write-Utf8Lf -Path (Join-Path $RunDir 'RunSummary.json') -Text ($Summary | ConvertTo-Json -Depth 12)
    Write-Utf8Lf -Path (Join-Path $RunDir 'error.txt') -Text "$_"
    Write-Host ''
    Write-Host "FAILED: $_" -ForegroundColor Red
    Write-Host "evidence: $RunDir"
    exit 1
}

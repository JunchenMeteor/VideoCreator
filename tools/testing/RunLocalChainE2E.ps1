#Requires -Version 7.0
<#
.SYNOPSIS
  One reproducible command for the LocalChainEndToEndTest role.

.DESCRIPTION
  Rebuilds (only when the checkout bytes moved) the suite's own registration
  fixture with the official integration builder, then runs the real test groups and
  records every child's raw stdout/stderr bytes and exit code:

    1. development-host refusals + health visibility
    2. new coverage: dev Owner auto-init, acceptance dispatch, zero-cost executor,
       media derivative request shape
    3. the positive end-to-end chain (runs only when a human is present to submit
       the two real review decisions; otherwise it is a recorded skip)

  The fixture is built in `-FixtureRoot` from the current checkout and a copy of a
  clean instance; the integration hand-off slice and its instance are never
  written. The script never confirms an Owner action, never patches `isatty`,
  never edits product source and never invokes a model.

.EXAMPLE
  pwsh -NoProfile -File ./RunLocalChainE2E.ps1

.EXAMPLE
  # Gate mode: exit 2 when the positive chain was skipped (no human reviewer), so a
  # green exit always means the full chain really ran.
  pwsh -NoProfile -File ./RunLocalChainE2E.ps1 -RequirePositive
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = 'G:/开发测试/Projects/VideoCreator',
    [string]$InstallationRoot = 'G:/开发测试/Codex/VideoCreatorImplementation/Integration/LocalInstallationRegistrationBuild',
    [string]$FixtureRoot = 'G:/开发测试/Codex/VideoCreatorImplementation/Test/LocalChainEndToEnd/Fixture',
    [string]$EvidenceRoot = 'G:/开发测试/Codex/VideoCreatorImplementation/Test/LocalChainEndToEnd/Evidence',
    [int]$TimeoutSeconds = 1800,
    [switch]$RequirePositive
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Python = Join-Path $RepoRoot '.venv/Scripts/python.exe'
$EngineSource = Join-Path $RepoRoot 'services/engine/src'
$FixtureTool = Join-Path $RepoRoot 'tools/testing/local_chain_fixture.py'
$Probes = Join-Path $RepoRoot 'tools/testing/local_chain_probes.py'
$Tests = Join-Path $RepoRoot 'tests/development'
$ProductFiles = @(
    'services/engine/src/video_creator/application/executor.py',
    'services/engine/src/video_creator/application/development_owner_initialization.py',
    'services/engine/src/video_creator/application/owner_bootstrap.py',
    'services/engine/src/video_creator/application/production_management.py',
    'services/engine/src/video_creator/application/engine.py',
    'services/engine/src/video_creator/cli/development_host.py',
    'services/engine/src/video_creator/workflows/local_material_drivers.py',
    'services/engine/src/video_creator/workflows/local_material_production.py'
)

$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$RunDir = Join-Path $EvidenceRoot "$Stamp-e2e"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$env:PYTHONPATH = $EngineSource
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:VIDEO_CREATOR_LOCAL_CHAIN_EVIDENCE = $RunDir
$env:VIDEO_CREATOR_LOCAL_FIXTURE = $FixtureRoot

$Summary = [ordered]@{
    started_at = (Get-Date).ToUniversalTime().ToString('o')
    stamp = $Stamp
    repo = $RepoRoot
    installation_hand_off = $InstallationRoot
    fixture_root = $FixtureRoot
    evidence = $RunDir
    python = $Python
    commands = @()
    versions = [ordered]@{}
    shas = [ordered]@{}
    product_file_sha256 = [ordered]@{}
    fixture = $null
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
    return [pscustomobject]@{ exit = $exit; stdout = $stdout; stderr = $stderr }
}

function Write-Utf8Lf([string]$Path, [string]$Text) {
    $normalized = ($Text -replace "`r`n", "`n") -replace "`r", "`n"
    [System.IO.File]::WriteAllText($Path, $normalized, [System.Text.UTF8Encoding]::new($false))
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-JsonFromFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $text = ([System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)).Trim()
    if (-not $text.StartsWith('{')) { return $null }
    try { return $text | ConvertFrom-Json } catch { return $null }
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
    $nested = @(Get-ChildItem -LiteralPath $RunDir -Directory |
        Where-Object { $_.Name -like '*-pytest-*' } | Sort-Object Name | Select-Object -Last 1)
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
    foreach ($required in @($Python, $FixtureTool, $Probes, $Tests, (Join-Path $InstallationRoot 'build_local_registration.py'))) {
        if (-not (Test-Path -LiteralPath $required)) { throw "required path missing: $required" }
    }
    Write-Host "evidence: $RunDir"

    Write-Step '1/6 registration fixture from the current checkout'
    $fixtureResult = Invoke-Recorded -Name 'fixture-ensure' -FilePath $Python `
        -Arguments @($FixtureTool, '--fixture-root', $FixtureRoot, '--integration', $InstallationRoot, 'ensure') `
        -Timeout $TimeoutSeconds
    $fixture = Get-JsonFromFile $fixtureResult.stdout
    if ($fixtureResult.exit -ne 0 -or $null -eq $fixture -or -not $fixture.ok) {
        $stderrText = [System.IO.File]::ReadAllText($fixtureResult.stderr, [System.Text.Encoding]::UTF8)
        throw "the registration fixture could not be made current (exit $($fixtureResult.exit)): $stderrText"
    }
    $Summary.fixture = $fixture
    $env:VIDEO_CREATOR_LOCAL_INSTALLATION = $fixture.fixture_root
    Remove-Item Env:VIDEO_CREATOR_LOCAL_INSTANCE -ErrorAction SilentlyContinue
    $Registration = Join-Path $fixture.fixture_root 'Registration.json'
    Write-Host "registration: $($fixture.registration_sha256) ($($fixture.engine_source_count) engine sources, rebuilt=$($fixture.rebuilt))"
    Write-Host "base instance: $($fixture.base_instance)"
    if ($fixture.fixture_root -eq $InstallationRoot) {
        throw 'the fixture must not write into the integration hand-off directory'
    }

    Write-Step '2/6 environment and artifact facts'
    $pythonVersion = Invoke-Recorded -Name 'version-python' -FilePath $Python -Arguments @('-VV')
    $ffmpegPath = Join-Path $fixture.fixture_root 'Package/Media/FFmpeg/bin/ffmpeg.exe'
    $ffprobePath = Join-Path $fixture.fixture_root 'Package/Media/FFmpeg/bin/ffprobe.exe'
    $ffmpegVersion = Invoke-Recorded -Name 'version-ffmpeg' -FilePath $ffmpegPath -Arguments @('-version')
    $ffprobeVersion = Invoke-Recorded -Name 'version-ffprobe' -FilePath $ffprobePath -Arguments @('-version')
    $gitHead = Invoke-Recorded -Name 'git-head' -FilePath 'git' -Arguments @('-C', $RepoRoot, 'rev-parse', 'HEAD')
    $gitStatus = Invoke-Recorded -Name 'git-status' -FilePath 'git' -Arguments @('-C', $RepoRoot, 'status', '--porcelain')
    $read = { param($path) [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8) }
    $Summary.versions['python'] = (((& $read $pythonVersion.stdout) -split "`n")[0]).Trim()
    $Summary.versions['ffmpeg'] = (((& $read $ffmpegVersion.stdout) -split "`n")[0]).Trim()
    $Summary.versions['ffprobe'] = (((& $read $ffprobeVersion.stdout) -split "`n")[0]).Trim()
    $Summary.shas['python_exit'] = $pythonVersion.exit
    $Summary.shas['ffmpeg_exit'] = $ffmpegVersion.exit
    $Summary.shas['ffprobe_exit'] = $ffprobeVersion.exit
    $Summary.shas['git_head'] = ((& $read $gitHead.stdout).Trim())
    $Summary.shas['git_status_porcelain'] = ((& $read $gitStatus.stdout).Trim())
    $Summary.shas['registration'] = $fixture.registration_sha256
    $Summary.shas['registration_bytes'] = $fixture.registration_bytes
    $Summary.shas['runtime_manifest'] = Get-Sha256 (Join-Path $fixture.fixture_root 'Package/RuntimeFileManifest.json')
    $Summary.shas['local_material_resources'] = Get-Sha256 (Join-Path $fixture.fixture_root 'Package/LocalMaterialResources.json')
    $Summary.shas['ffmpeg'] = Get-Sha256 $ffmpegPath
    $Summary.shas['ffprobe'] = Get-Sha256 $ffprobePath
    $Summary.shas['fixture_builder'] = $fixture.builder_sha256
    $Summary.shas['fixture_checker'] = $fixture.checker_sha256
    foreach ($relative in $ProductFiles) {
        $Summary.product_file_sha256[$relative] = Get-Sha256 (Join-Path $RepoRoot $relative)
    }
    Write-Host "python:  $($Summary.versions['python'])"
    Write-Host "ffmpeg:  $($Summary.versions['ffmpeg'])"
    Write-Host "ffprobe: $($Summary.versions['ffprobe'])"
    Write-Host "HEAD:    $($Summary.shas['git_head'])"

    Write-Step '3/6 development-host refusals + health visibility'
    $negatives = Invoke-Pytest -Name 'pytest-negatives' -Targets @(
        (Join-Path $Tests 'test_development_host_negatives.py'),
        (Join-Path $Tests 'test_development_host_health.py'))
    Write-Host "negatives exit=$($negatives.exit) counts=$(($negatives.counts | ConvertTo-Json -Compress))"

    Write-Step '4/6 new coverage: owner auto-init, acceptance dispatch, executor, media request'
    $coverage = Invoke-Pytest -Name 'pytest-new-coverage' -Targets @(
        (Join-Path $Tests 'test_development_owner_auto_init.py'),
        (Join-Path $Tests 'test_acceptance_dispatch.py'),
        (Join-Path $Tests 'test_executor_zero_cost.py'),
        (Join-Path $Tests 'test_media_derivative_request.py'))
    Write-Host "coverage exit=$($coverage.exit) counts=$(($coverage.counts | ConvertTo-Json -Compress))"

    Write-Step '5/6 positive local chain (needs a human reviewer)'
    $positive = Invoke-Pytest -Name 'pytest-local-chain' -Targets @((Join-Path $Tests 'test_local_chain_end_to_end.py'))
    $positiveSkipped = ($null -ne $positive.counts) -and ($positive.counts.skipped -gt 0) -and ($positive.counts.failures -eq 0)
    if ($positiveSkipped) {
        $reason = 'no human reviewer is present to submit the two real review decisions'
        Write-Host 'The positive chain was skipped: it needs real human review decisions; this script never approves on a human behalf.' -ForegroundColor Yellow
        $Summary.not_executed += [ordered]@{
            case = 'tests/development/test_local_chain_end_to_end.py::test_local_chain_produces_a_verifiable_0_4_bundle'
            reason = $reason
            fix = 'set VIDEO_CREATOR_HUMAN_APPROVAL=1 with a person at the API, or run the review steps by hand'
        }
    }
    Write-Host "positive exit=$($positive.exit) counts=$(($positive.counts | ConvertTo-Json -Compress))"

    Write-Step '6/6 evidence inventory and summary'
    $inventory = Get-ChildItem -LiteralPath $RunDir -File | ForEach-Object {
        [ordered]@{ name = $_.Name; bytes = $_.Length; sha256 = (Get-Sha256 $_.FullName) }
    }
    $Summary.shas['evidence_files'] = @($inventory).Count
    Write-Utf8Lf -Path (Join-Path $RunDir 'EvidenceInventory.json') -Text ($inventory | ConvertTo-Json -Depth 5)

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
    Write-Host "executed failures: $executedFailure; positive skipped: $positiveSkipped"

    if ($executedFailure) { exit 1 }
    if ($RequirePositive -and $positiveSkipped) {
        Write-Host 'RequirePositive was set but the positive chain did not run (no human reviewer).' -ForegroundColor Red
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

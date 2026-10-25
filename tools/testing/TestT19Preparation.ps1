param([Parameter(Mandatory)][string]$OutputDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$owned = 'G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/BusinessHarness-T19'
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
if (-not $output.StartsWith([System.IO.Path]::GetFullPath($owned) + [System.IO.Path]::DirectorySeparatorChar) -or (Test-Path -LiteralPath $output)) { throw 'OWN_FRESH_PREPARATION_DIRECTORY_REQUIRED' }
$null = New-Item -ItemType Directory -Path $output
$repo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$paths = @(
    (Join-Path $PSScriptRoot 'T19LaunchRules.psm1'),
    (Join-Path $PSScriptRoot 'StartT19Business.ps1'),
    (Join-Path $PSScriptRoot 'T19BusinessHarness.py'),
    $PSCommandPath,
    (Join-Path $repo 'tests/bundle/t19_business_cases.py'),
    (Join-Path $repo 'tests/bundle/t19_bundle_cases.py'),
    (Join-Path $repo 'tests/bundle/t19_transport_cases.py')
)
$hostPath = (Get-Process -Id $PID).Path
$paths += $hostPath
$before = @{}
$sourceCopies = @()
foreach ($path in $paths) {
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $before[$path] = $hash
    if ($path -ne $hostPath) {
        $target = Join-Path $output ("SourceBefore/" + [System.IO.Path]::GetFileName($path))
        $null = New-Item -ItemType Directory -Path (Split-Path $target) -Force
        [System.IO.File]::WriteAllBytes($target, [System.IO.File]::ReadAllBytes($path))
        $sourceCopies += @{ source_path = $path; body_copy = $target; sha256 = $hash }
    }
}
$utf8 = [System.Text.UTF8Encoding]::new($false)
function Save-Json($Name, $Value) { [System.IO.File]::WriteAllText((Join-Path $output $Name), ($Value | ConvertTo-Json -Depth 32) + "`n", $utf8) }
Save-Json 'LaunchBefore.json' @{ started_at = [DateTime]::UtcNow.ToString('o'); tool_pid = $PID; tool_creation = (Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('o'); argv = @($PSCommandPath,'-OutputDirectory',$OutputDirectory); identities = $before; source_copies = $sourceCopies; product_launch_allowed = $false }
Import-Module (Join-Path $PSScriptRoot 'T19LaunchRules.psm1') -Force
$rows = [System.Collections.Generic.List[object]]::new()
function Check($Name, [scriptblock]$Action, [string]$Expected = '') {
    try {
        $null = & $Action
        if ($Expected) { throw "EXPECTED_REFUSAL_MISSING:$Expected" }
        $rows.Add(@{ name = $Name; pass = $true; classification = 'own fixture preparation only' })
    } catch {
        $message = $_.Exception.Message
        $pass = [bool]($Expected -and $message -match $Expected)
        $rows.Add(@{ name = $Name; pass = $pass; actual_error = $message; expected = $Expected; classification = 'own fixture preparation only' })
    }
}
$fixture = Join-Path $output 'Fixture'
$sourceRoot = Join-Path $fixture 'Source'
$resourceRoot = Join-Path $fixture 'Resources'
$bodyRoot = Join-Path $fixture 'Bodies'
$null = New-Item -ItemType Directory -Path (Join-Path $sourceRoot 'video_creator/application'),$resourceRoot,$bodyRoot -Force
$sourceMap = @{}
$records = @()
foreach ($relative in @('video_creator/__init__.py','video_creator/application/__init__.py','video_creator/application/bundles.py')) {
    $path = [System.IO.Path]::GetFullPath((Join-Path $sourceRoot $relative))
    [System.IO.File]::WriteAllText($path, "MARKER = 'owned plain file, never imported'`n", $utf8)
    $sha = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $sourceMap[$path] = $sha
    $copy = Join-Path $bodyRoot ($relative.Replace('/','-'))
    [System.IO.File]::WriteAllBytes($copy, [System.IO.File]::ReadAllBytes($path))
    $records += @{ source_path = $path; body_copy = $copy }
}
$resource = Join-Path $resourceRoot 'Marker.bin'
[System.IO.File]::WriteAllText($resource, 'not an executable, no product data', $utf8)
$resourceMap = @{ $resource = (Get-FileHash -LiteralPath $resource -Algorithm SHA256).Hash.ToLowerInvariant() }
$chain = @(
    @{ module = 'video_creator'; path = Join-Path $sourceRoot 'video_creator/__init__.py' },
    @{ module = 'video_creator.application'; path = Join-Path $sourceRoot 'video_creator/application/__init__.py' },
    @{ module = 'video_creator.application.bundles'; path = Join-Path $sourceRoot 'video_creator/application/bundles.py' }
)
$binding = @{ required_sources = $sourceMap; required_resources = $resourceMap; target_module = 'video_creator.application.bundles'; target_path = $chain[2].path; source_root = $sourceRoot; module_chain = $chain; source_directory_scopes = @(@{root=$sourceRoot; pattern='*.py'}); resource_directory_scopes = @(@{root=$resourceRoot; pattern='*'}) }
$admission = @{ production_and_test_sources = $sourceMap; runtime_resources = $resourceMap; paid_provider_calls_allowed = $false }
Check 'complete-own-file-fixture-check-only-no-authority' { Assert-T19ClosedInputs $binding $admission $records $output }
$strict = Join-Path $fixture 'JsonInput.json'
foreach ($test in @(
    @{name='duplicate-governance-key'; raw='{"x":1,"x":2}'; error='T19_DUPLICATE_JSON_KEY'},
    @{name='positive-exponent-overflow'; raw='{"x":1e999}'; error='T19_NONFINITE_JSON_NUMBER'},
    @{name='negative-exponent-overflow'; raw='{"x":-1e999}'; error='T19_NONFINITE_JSON_NUMBER'},
    @{name='nested-exponent-overflow'; raw='{"x":[{"nested":1e999}]}'; error='T19_NONFINITE_JSON_NUMBER'}
)) {
    [System.IO.File]::WriteAllText($strict, $test.raw, $utf8)
    Check $test.name { Read-T19StrictJson $strict } $test.error
}
Check 'missing-closure-resource-set' { Assert-T19ExactIdentityMap @{} @{} } 'T19_NONEMPTY_CLOSURE_REQUIRED'
$altered = @{}
foreach ($key in $sourceMap.Keys) { $altered[$key] = $sourceMap[$key] }
$null = $altered.Remove($chain[0].path)
Check 'admission-cannot-shrink-approved-source-set' { Assert-T19ExactIdentityMap $sourceMap $altered } 'T19_CLOSURE_SET_MISMATCH'
$original = [System.IO.File]::ReadAllBytes($chain[2].path)
[System.IO.File]::AppendAllText($chain[2].path, 'changed', $utf8)
Check 'actual-source-hash-drift' { Assert-T19ClosedInputs $binding $admission $records $output } 'T19_FILE_HASH_CHANGED'
[System.IO.File]::WriteAllBytes($chain[2].path, $original)
$resourceBytes = [System.IO.File]::ReadAllBytes($resource)
[System.IO.File]::AppendAllText($resource, 'changed', $utf8)
Check 'actual-resource-hash-drift' { Assert-T19ClosedInputs $binding $admission $records $output } 'T19_FILE_HASH_CHANGED'
[System.IO.File]::WriteAllBytes($resource, $resourceBytes)
Check 'body-archive-missing-entry' { Assert-T19ClosedInputs $binding $admission @($records[0],$records[1]) $output } 'T19_SOURCE_BODY_SET_MISMATCH'
$hook = Join-Path $resourceRoot 'Unlisted.pth'
[System.IO.File]::WriteAllText($hook, '# owned marker; never processed by Python', $utf8)
Check 'unlisted-startup-hook-directory-file' { Assert-T19ClosedInputs $binding $admission $records $output } 'T19_UNLISTED_DIRECTORY_FILE'
[System.IO.File]::Delete($hook)
$badChain = @($chain[0],$chain[2])
$badBinding = $binding.Clone()
$badBinding.module_chain = $badChain
Check 'target-without-complete-parent-chain' { Assert-T19ClosedInputs $badBinding $admission $records $output } 'T19_PARENT_PACKAGE_MISSING'
$authority = Join-Path $repo 'docs/task-board/T19RuntimeAuthorization.json'
if (Test-Path -LiteralPath $authority) { throw 'ROOT_RUNTIME_RECORD_EXISTS_PREPARATION_WILL_NOT_LAUNCH_STARTER' }
Check 'real-starter-refuses-before-python' {
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $hostPath
    foreach ($argument in @('-NoProfile','-NonInteractive','-File',(Join-Path $PSScriptRoot 'StartT19Business.ps1'),'-Batch','service-negative')) { $start.ArgumentList.Add($argument) }
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    if (-not $process.Start()) { throw 'PREPARATION_POWERSHELL_CHILD_NOT_STARTED' }
    $childPid = $process.Id
    $childCreation = $process.StartTime.ToUniversalTime().ToString('o')
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(15000)) { throw 'PREPARATION_POWERSHELL_CHILD_TIMEOUT' }
    $raw = $stdout.GetAwaiter().GetResult()
    [System.IO.File]::WriteAllText((Join-Path $output 'StarterStdout.txt'), $raw, $utf8)
    [System.IO.File]::WriteAllText((Join-Path $output 'StarterStderr.txt'), $stderr.GetAwaiter().GetResult(), $utf8)
    Save-Json 'StarterChildReceipt.json' @{ argv = @($start.FileName) + @($start.ArgumentList); pid = $childPid; actual_start_time = $childCreation; actual_exit = $process.ExitCode; has_exited = $process.HasExited; product_python_spawned = $false; classification = 'real PowerShell preparation child, not Python/product' }
    if ($process.ExitCode -ne 78) { throw 'STARTER_DID_NOT_REFUSE_NOT_READY' }
    $result = $raw | ConvertFrom-Json -AsHashtable
    if ($result.python_spawned -or $result.code -cne 'T19_ROOT_AUTHORIZATION_NOT_PUBLISHED') { throw 'STARTER_CROSSED_PRE_PYTHON_BOUNDARY' }
}
$changed = @()
foreach ($path in $paths) { if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $before[$path]) { $changed += $path } }
$failed = @($rows | Where-Object { -not $_.pass })
$receipt = @{ checks = $rows; failures = $failed.Count; actual_checks = $rows.Count; source_tool_changes = $changed; product_import_ASR_service_CLI_API_MCP = 0; fees_keys_install_network = 0; launched_only_one_owned_PowerShell_preparation_child = $true; evidence_scope = 'new pre-Python rules own-file negative checks only, not actual producer/ABI/runtime approval'; ended_at = [DateTime]::UtcNow.ToString('o'); exit = $(if ($failed.Count -or $changed.Count) {1} else {0}) }
Save-Json 'Receipt.json' $receipt
$receipt | ConvertTo-Json -Depth 32
exit $receipt.exit

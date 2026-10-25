[CmdletBinding()]
param([Parameter(Mandatory)][ValidateSet('service-negative','transport-negative','qualified-bundle','bundle-consume','bundle-correction','bundle-runtime-gap')][string]$Batch)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$t19Repo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$t19Own = 'G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/BusinessHarness-T19'
# This path belongs to ROOT by AGENTS, never to ordinary caller/admission/Test.
# No CLI flag accepts authority files or expected hashes from a caller.
$t19RootAuthority = Join-Path $t19Repo 'docs/task-board/T19RuntimeAuthorization.json'
$t19Spawned = $false
$t19Captured = @()
$t19Child = $null
$t19FirstCleanup = $null
function Read-T19BootstrapHeader([string]$Path) {
    # Built-in parser in the already trusted entry; never load a helper module
    # merely to discover its expected hash. No caller can choose this header.
    $raw = [System.IO.File]::ReadAllBytes($Path)
    if ($raw.Length -gt 67108864) { throw 'T19_HEADER_SIZE_DENIED' }
    $text = [System.Text.UTF8Encoding]::new($false, $true).GetString($raw)
    $options = [System.Text.Json.JsonDocumentOptions]::new()
    $options.MaxDepth = 64
    $document = [System.Text.Json.JsonDocument]::Parse($text, $options)
    function Check-HeaderElement([System.Text.Json.JsonElement]$Element) {
        if ($Element.ValueKind.ToString() -eq 'Object') {
            $names = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
            foreach ($property in $Element.EnumerateObject()) {
                if (-not $names.Add($property.Name)) { throw 'T19_HEADER_DUPLICATE_KEY' }
                Check-HeaderElement $property.Value
            }
        } elseif ($Element.ValueKind.ToString() -eq 'Array') {
            foreach ($item in $Element.EnumerateArray()) { Check-HeaderElement $item }
        } elseif ($Element.ValueKind.ToString() -eq 'Number') {
            $number = 0.0
            if (-not $Element.TryGetDouble([ref]$number) -or [double]::IsInfinity($number) -or [double]::IsNaN($number)) { throw 'T19_HEADER_NONFINITE_NUMBER' }
        }
    }
    try { Check-HeaderElement $document.RootElement } finally { $document.Dispose() }
    return ConvertFrom-Json -InputObject $text -AsHashtable -Depth 64
}
try {
    if (-not (Test-Path -LiteralPath $t19RootAuthority -PathType Leaf)) { throw 'T19_ROOT_AUTHORIZATION_NOT_PUBLISHED' }
    $header = Read-T19BootstrapHeader $t19RootAuthority
    if ($header.status -cne 'ROOT_APPROVED_EXACT_RUNTIME' -or $Batch -notin $header.batches -or $header.rules_sha256 -cnotmatch '^[a-f0-9]{64}$' -or $header.starter_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'T19_ROOT_HEADER_NOT_APPROVED' }
    if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $header.starter_sha256 -or (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'T19LaunchRules.psm1') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $header.rules_sha256) { throw 'T19_ENTRY_OR_HELPER_CHANGED_BEFORE_MODULE_LOAD' }
    $headerReviewPath = [System.IO.Path]::GetFullPath($header.independent_review.path)
    $headerReviewRoot = [System.IO.Path]::GetFullPath((Join-Path $t19Repo 'docs/reviews')) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $headerReviewPath.StartsWith($headerReviewRoot, [System.StringComparison]::OrdinalIgnoreCase) -or (Get-FileHash -LiteralPath $headerReviewPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $header.independent_review.sha256) { throw 'T19_REVIEW_HEADER_SOURCE_OR_HASH_DENIED' }
    $headerReview = Read-T19BootstrapHeader $headerReviewPath
    if ($headerReview.status -cne 'APPROVED_EXACT_RUNTIME_BINDING' -or $Batch -notin $headerReview.batches -or $headerReview.starter_sha256 -cne $header.starter_sha256 -or $headerReview.rules_sha256 -cne $header.rules_sha256) { throw 'T19_HELPER_NOT_INDEPENDENTLY_APPROVED' }
    Import-Module (Join-Path $PSScriptRoot 'T19LaunchRules.psm1') -Force
    $root = Read-T19StrictJson $t19RootAuthority
    if ($root.status -cne 'ROOT_APPROVED_EXACT_RUNTIME' -or $Batch -notin $root.batches -or $root.fees_cny -cne '0') { throw 'T19_ROOT_SCOPE_NOT_APPROVED' }
    $null = Assert-T19FileIdentity $PSCommandPath $root.starter_sha256
    $null = Assert-T19FileIdentity (Join-Path $PSScriptRoot 'T19LaunchRules.psm1') $root.rules_sha256
    $reviewPath = Get-T19CanonicalPath $root.independent_review.path
    $reviewRoot = (Get-T19CanonicalPath (Join-Path $t19Repo 'docs/reviews')) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $reviewPath.StartsWith($reviewRoot, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'T19_REVIEW_SOURCE_DENIED' }
    $null = Assert-T19FileIdentity $reviewPath $root.independent_review.sha256
    $review = Read-T19StrictJson $reviewPath
    if ($review.status -cne 'APPROVED_EXACT_RUNTIME_BINDING' -or $Batch -notin $review.batches -or $review.binding_sha256 -cne $root.binding.sha256 -or $review.admission_sha256 -cne $root.admission.sha256 -or $review.starter_sha256 -cne $root.starter_sha256 -or $review.rules_sha256 -cne $root.rules_sha256) { throw 'T19_INDEPENDENT_RUNTIME_APPROVAL_MISSING' }
    foreach ($item in @($root.binding, $root.admission)) {
        $path = Assert-T19FileIdentity $item.path $item.sha256
        if (-not $path.StartsWith((Get-T19CanonicalPath $t19Own) + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'T19_BINDING_NOT_TEST_OWNED' }
    }
    $binding = Read-T19StrictJson $root.binding.path
    $admission = Read-T19StrictJson $root.admission.path
    $t19DataDir = Get-T19CanonicalPath $admission.own_data_dir
    $null = Assert-T19OwnedWriteTarget -Path $t19DataDir -OwnedRoot $t19Own
    $null = Assert-T19FileIdentity $admission.prelaunch_source_body_manifest $admission.prelaunch_source_body_manifest_sha256
    $bodies = Read-T19StrictJson $admission.prelaunch_source_body_manifest
    $closed = Assert-T19ClosedInputs $binding $admission $bodies.files $t19Own
    $python = Get-T19CanonicalPath $binding.service_python
    if ($python -ine (Get-T19CanonicalPath (Join-Path $t19Repo '.venv/Scripts/python.exe')) -or (Get-T19CanonicalPath $binding.migrations_dir) -ine (Get-T19CanonicalPath (Join-Path $t19Repo 'services/engine/migrations'))) { throw 'T19_FIXED_PYTHON_OR_MIGRATIONS_REQUIRED' }
    $harness = Get-T19CanonicalPath (Join-Path $t19Repo 'tools/testing/T19BusinessHarness.py')
    $t19HostPath = (Get-Process -Id $PID).Path
    if (-not $closed.Resources.ContainsKey($python) -or -not $closed.Resources.ContainsKey((Get-T19CanonicalPath $t19HostPath)) -or -not $closed.Sources.ContainsKey($harness)) { throw 'T19_PYTHON_HOST_HARNESS_NOT_BOUND' }
    $null = Assert-T19FileIdentity $python $closed.Resources[$python]
    $output = Get-T19CanonicalPath $root.output_dir
    $cache = Join-Path $output 'PythonCache'
    $t19Protected = @($closed.Sources.Keys) + @($closed.Resources.Keys) + @($bodies.files | ForEach-Object { $_.body_copy }) + @($t19RootAuthority, $reviewPath, $root.binding.path, $root.admission.path, $admission.prelaunch_source_body_manifest)
    $null = Assert-T19OwnedWriteTarget -Path $t19DataDir -OwnedRoot $t19Own -ProtectedPaths $t19Protected
    $null = Assert-T19OwnedWriteTarget -Path $output -OwnedRoot $t19Own -ProtectedPaths $t19Protected -RequireAbsent
    $null = Assert-T19OwnedWriteTarget -Path $cache -OwnedRoot $t19Own -ProtectedPaths $t19Protected -RequireAbsent
    foreach ($t19ReceiptName in @('PrePythonReceipt.json','PythonStdout.txt','PythonStderr.txt','StarterTerminalReceipt.json','StarterFailureReceipt.json')) {
        $null = Assert-T19OwnedWriteTarget -Path (Join-Path $output $t19ReceiptName) -OwnedRoot $t19Own -ProtectedPaths $t19Protected -RequireAbsent -FileTarget
    }
    # The exact interpreter/profile/starter approval is fixed before creating a
    # child; source directories and runtime/site files have already been checked.
    $null = New-Item -ItemType Directory -Path $output
    $null = Assert-T19OwnedWriteTarget -Path $cache -OwnedRoot $t19Own -ProtectedPaths $t19Protected -RequireAbsent
    $null = New-Item -ItemType Directory -Path $cache
    $ownProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
    $receipt = @{ root_authorization_sha256 = (Get-FileHash -LiteralPath $t19RootAuthority -Algorithm SHA256).Hash.ToLowerInvariant(); binding_sha256 = $root.binding.sha256; admission_sha256 = $root.admission.sha256; batch = $Batch; pre_python_sources = $closed.Sources.Count; pre_python_resources = $closed.Resources.Count; starter_pid = $PID; starter_creation = $ownProcess.CreationDate.ToUniversalTime().ToString('o'); python_spawned = $false; started_at = [DateTime]::UtcNow.ToString('o') }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText((Join-Path $output 'PrePythonReceipt.json'), ($receipt | ConvertTo-Json -Depth 16) + "`n", $utf8)
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $python
    foreach ($argument in @('-I','-S','-B','-X','utf8','-X',"pycache_prefix=$cache",$harness,'--batch',$Batch,'--output',$output)) { $start.ArgumentList.Add($argument) }
    $start.WorkingDirectory = $output
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.Environment.Clear()
    $start.Environment['SystemRoot'] = [Environment]::GetFolderPath('Windows')
    $start.Environment['WINDIR'] = [Environment]::GetFolderPath('Windows')
    $start.Environment['PATH'] = [Environment]::SystemDirectory
    $start.Environment['TEMP'] = $output
    $start.Environment['TMP'] = $output
    $start.Environment['VIDEO_CREATOR_MIGRATIONS_DIR'] = $binding.migrations_dir
    $child = [System.Diagnostics.Process]::new()
    $t19Child = $child
    $child.StartInfo = $start
    if (-not $child.Start()) { throw 'T19_CHILD_START_FAILED' }
    $t19Spawned = $true
    $childIdentity = Get-CimInstance Win32_Process -Filter "ProcessId=$($child.Id)"
    if ($null -eq $childIdentity) { throw 'T19_CHILD_CREATION_NOT_CAPTURED' }
    $receipt.python_spawned = $true
    $receipt.python_pid = $child.Id
    $receipt.python_creation = $childIdentity.CreationDate.ToUniversalTime().ToString('o')
    $t19Captured = @(@{ pid = $child.Id; parent = $PID; creation = $receipt.python_creation })
    [System.IO.File]::WriteAllText((Join-Path $output 'PrePythonReceipt.json'), ($receipt | ConvertTo-Json -Depth 16) + "`n", $utf8)
    $stdout = $child.StandardOutput.ReadToEndAsync()
    $stderr = $child.StandardError.ReadToEndAsync()
    $deadline = [DateTime]::UtcNow.AddSeconds(300)
    while (-not $child.WaitForExit(250)) {
        foreach ($captured in @(Get-T19OwnedSnapshot $child.Id $receipt.python_creation)) {
            if (-not @($t19Captured | Where-Object { $_.pid -eq $captured.pid -and $_.creation -ceq $captured.creation })) { $t19Captured += $captured }
        }
        if ([DateTime]::UtcNow -ge $deadline) { throw 'T19_CHILD_TIMEOUT' }
    }
    [System.IO.File]::WriteAllText((Join-Path $output 'PythonStdout.txt'), $stdout.GetAwaiter().GetResult(), $utf8)
    [System.IO.File]::WriteAllText((Join-Path $output 'PythonStderr.txt'), $stderr.GetAwaiter().GetResult(), $utf8)
    $receipt.actual_exit = $child.ExitCode
    $cleanup = Stop-T19CapturedTree $t19Captured
    $t19FirstCleanup = $cleanup
    $receipt.cleanup = $cleanup
    if (-not $cleanup.verified_captured_terminal -or $cleanup.forced_pids.Count -gt 0) { throw 'T19_FORCED_OR_UNVERIFIED_TREE_NOT_NORMAL' }
    $null = Assert-T19ClosedInputs $binding $admission $bodies.files $t19Own
    $null = Assert-T19FileIdentity $root.binding.path $root.binding.sha256
    $null = Assert-T19FileIdentity $root.admission.path $root.admission.sha256
    $null = Assert-T19FileIdentity $reviewPath $root.independent_review.sha256
    if ((Get-FileHash -LiteralPath $t19RootAuthority -Algorithm SHA256).Hash.ToLowerInvariant() -cne $receipt.root_authorization_sha256) { throw 'T19_AUTHORIZATION_CHANGED_DURING_BATCH' }
    $receipt.ended_at = [DateTime]::UtcNow.ToString('o')
    [System.IO.File]::WriteAllText((Join-Path $output 'StarterTerminalReceipt.json'), ($receipt | ConvertTo-Json -Depth 16) + "`n", $utf8)
    exit $child.ExitCode
} catch {
    # No caller supplies a binding/hash/root authority override. Denial is not a
    # skip/pass and never launches Python merely to find out it was unapproved.
    $reason = $_.Exception.Message
    $failure = @{ status = $(if ($t19Spawned) { 'failed_or_unknown_cleanup' } else { 'not_ready_for_execution' }); code = $reason; python_spawned = $t19Spawned; batch = $Batch }
    if ($t19Spawned) {
        if ($null -ne $t19FirstCleanup) { $failure.first_cleanup_observation = $t19FirstCleanup }
        try { $failure.cleanup = Stop-T19CapturedTree $t19Captured } catch { $failure.cleanup = @{ verified_captured_terminal = $false; code = $_.Exception.Message; no_unverified_force = $true } }
        if ($null -ne $t19Child -and $t19Child.HasExited) { $failure.actual_child_exit = $t19Child.ExitCode }
        if ($null -ne (Get-Variable -Name output -ErrorAction SilentlyContinue) -and (Test-Path -LiteralPath $output)) {
            [System.IO.File]::WriteAllText((Join-Path $output 'StarterFailureReceipt.json'), ($failure | ConvertTo-Json -Depth 16) + "`n", [System.Text.UTF8Encoding]::new($false))
        }
    }
    $failure | ConvertTo-Json -Compress -Depth 16
    if ($t19Spawned) { exit 1 } else { exit 78 }
}

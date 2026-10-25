Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Read-T19StrictJson {
    param([Parameter(Mandatory)][string]$Path)
    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.PSIsContainer -or $item.Length -gt 67108864) { throw 'T19_JSON_SIZE_DENIED' }
    $raw = [System.IO.File]::ReadAllBytes($item.FullName)
    $utf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $text = $utf8.GetString($raw)
    $options = [System.Text.Json.JsonDocumentOptions]::new()
    $options.MaxDepth = 64
    $doc = [System.Text.Json.JsonDocument]::Parse($text, $options)
    function Test-Element([System.Text.Json.JsonElement]$Element) {
        switch ($Element.ValueKind.ToString()) {
            'Object' {
                $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
                foreach ($property in $Element.EnumerateObject()) {
                    if (-not $seen.Add($property.Name)) { throw 'T19_DUPLICATE_JSON_KEY' }
                    Test-Element $property.Value
                }
            }
            'Array' { foreach ($element in $Element.EnumerateArray()) { Test-Element $element } }
            'Number' {
                $number = 0.0
                if (-not $Element.TryGetDouble([ref]$number) -or [double]::IsNaN($number) -or [double]::IsInfinity($number)) {
                    throw 'T19_NONFINITE_JSON_NUMBER'
                }
            }
        }
    }
    try { Test-Element $doc.RootElement } finally { $doc.Dispose() }
    return ConvertFrom-Json -InputObject $text -AsHashtable -Depth 64
}

function Get-T19CanonicalPath {
    param([Parameter(Mandatory)][string]$Path)
    if (-not [System.IO.Path]::IsPathFullyQualified($Path) -or $Path.StartsWith('\\') -or $Path.StartsWith('//')) {
        throw 'T19_ABSOLUTE_LOCAL_PATH_REQUIRED'
    }
    return [System.IO.Path]::GetFullPath($Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
}

function Assert-T19OwnedWriteTarget {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$OwnedRoot,
          [string[]]$ProtectedPaths = @(), [switch]$RequireAbsent, [switch]$FileTarget)
    # Read-only preflight: inspect left-to-right, before traversing a link.
    # This is not an OS sandbox and cannot eliminate filesystem TOCTOU.
    $canonical = Get-T19CanonicalPath $Path
    $owned = Get-T19CanonicalPath $OwnedRoot
    $prefix = $owned + [System.IO.Path]::DirectorySeparatorChar
    if (-not $canonical.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'T20_WRITE_OUTSIDE_OWN_ROOT' }
    foreach ($protected in $ProtectedPaths) {
        $closed = Get-T19CanonicalPath $protected
        if ($canonical -ieq $closed -or $canonical.StartsWith($closed + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -or $closed.StartsWith($canonical + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'T20_WRITE_OVERLAPS_CLOSED_INPUT' }
    }
    $driveRoot = [System.IO.Path]::GetPathRoot($canonical)
    $components = $canonical.Substring($driveRoot.Length).Split([char[]]@('\','/'), [System.StringSplitOptions]::RemoveEmptyEntries)
    foreach ($component in $components) {
        if ($component.Contains(':') -or $component.EndsWith('.') -or $component.EndsWith(' ')) { throw 'T20_WRITE_AMBIGUOUS_COMPONENT' }
    }
    $cursor = $driveRoot
    $existing = Get-Item -LiteralPath $cursor -Force -ErrorAction Stop
    if (-not $existing.PSIsContainer -or ($existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) { throw 'T20_WRITE_ROOT_INVALID' }
    $existingParent = $existing.FullName
    $missing = $false
    for ($index = 0; $index -lt $components.Length; $index++) {
        $cursor = Join-Path $cursor $components[$index]
        if ($missing -or -not (Test-Path -LiteralPath $cursor -ErrorAction Stop)) { $missing = $true; continue }
        $existing = Get-Item -LiteralPath $cursor -Force -ErrorAction Stop
        if ($existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'T20_WRITE_PARENT_LINK_DENIED' }
        $last = $index -eq $components.Length - 1
        if (-not $last -and -not $existing.PSIsContainer) { throw 'T20_WRITE_PARENT_NOT_DIRECTORY' }
        if ($last -and $RequireAbsent) { throw 'T20_FRESH_WRITE_TARGET_REQUIRED' }
        if ($last -and -not $FileTarget -and -not $existing.PSIsContainer) { throw 'T20_DIRECTORY_WRITE_TARGET_REQUIRED' }
        if ($last -and $FileTarget -and $existing.PSIsContainer) { throw 'T20_FILE_WRITE_TARGET_REQUIRED' }
        if ($existing.PSIsContainer) { $existingParent = $existing.FullName }
    }
    return @{ target = $canonical; existing_parent = $existingParent; complete_existing_parent_chain_checked = $true; links_allowed = $false; scope = 'read-only path preflight, not filesystem containment or race elimination' }
}

function Assert-T19FileIdentity {
    param([string]$Path, [string]$Sha256)
    if ($Sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'T19_HASH_FORMAT_DENIED' }
    $canonical = Get-T19CanonicalPath $Path
    $item = Get-Item -LiteralPath $canonical -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) { throw 'T19_LINK_OR_DIRECTORY_DENIED' }
    for ($parent = $item.Directory; $null -ne $parent; $parent = $parent.Parent) {
        if ($parent.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'T19_PARENT_LINK_DENIED' }
    }
    if ((Get-FileHash -LiteralPath $canonical -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Sha256) {
        throw 'T19_FILE_HASH_CHANGED'
    }
    return $canonical
}

function ConvertTo-T19IdentityMap {
    param($Map)
    if ($Map -isnot [System.Collections.IDictionary] -or $Map.Count -eq 0) { throw 'T19_NONEMPTY_CLOSURE_REQUIRED' }
    $result = [System.Collections.Generic.Dictionary[string,string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($key in $Map.Keys) {
        $canonical = Get-T19CanonicalPath ([string]$key)
        if ($result.ContainsKey($canonical) -or $Map[$key] -isnot [string] -or $Map[$key] -cnotmatch '^[a-f0-9]{64}$') {
            throw 'T19_CLOSURE_IDENTITY_INVALID'
        }
        $result.Add($canonical, $Map[$key])
    }
    return ,$result
}

function Assert-T19ExactIdentityMap {
    param($Required, $Actual)
    $requiredMap = ConvertTo-T19IdentityMap $Required
    $actualMap = ConvertTo-T19IdentityMap $Actual
    if ($requiredMap.Count -ne $actualMap.Count) { throw 'T19_CLOSURE_SET_MISMATCH' }
    foreach ($path in $requiredMap.Keys) {
        if (-not $actualMap.ContainsKey($path) -or $actualMap[$path] -cne $requiredMap[$path]) { throw 'T19_CLOSURE_SET_MISMATCH' }
        $null = Assert-T19FileIdentity $path $requiredMap[$path]
    }
    return ,$requiredMap
}

function Assert-T19DirectorySets {
    param($Scopes, $Map)
    if (-not $Scopes -or $Scopes.Count -eq 0) { throw 'T19_COMPLETE_DIRECTORY_SCOPES_REQUIRED' }
    foreach ($scope in $Scopes) {
        $root = Get-T19CanonicalPath $scope.root
        $rootItem = Get-Item -LiteralPath $root -ErrorAction Stop
        if (-not $rootItem.PSIsContainer -or ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) { throw 'T19_DIRECTORY_ROOT_INVALID' }
        $pattern = $scope.pattern
        if ($pattern -notin @('*', '*.py', '*.sql', '*.ps1', '*.psm1')) { throw 'T19_DIRECTORY_PATTERN_DENIED' }
        $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        foreach ($item in Get-ChildItem -LiteralPath $root -Recurse -Force -ErrorAction Stop) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'T19_DIRECTORY_LINK_DENIED' }
            if (-not $item.PSIsContainer -and $item.Name -like $pattern) {
                $path = Get-T19CanonicalPath $item.FullName
                if (-not $Map.ContainsKey($path)) { throw 'T19_UNLISTED_DIRECTORY_FILE' }
                $null = $seen.Add($path)
            }
        }
        $prefix = $root + [System.IO.Path]::DirectorySeparatorChar
        foreach ($path in $Map.Keys) {
            if ($path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase) -and [System.IO.Path]::GetFileName($path) -like $pattern -and -not $seen.Contains($path)) {
                throw 'T19_MISSING_DIRECTORY_FILE'
            }
        }
    }
}

function Assert-T19SourceBodies {
    param($SourceMap, $Records, [string]$OwnedRoot)
    if ($Records.Count -ne $SourceMap.Count) { throw 'T19_SOURCE_BODY_SET_MISMATCH' }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $prefix = (Get-T19CanonicalPath $OwnedRoot) + [System.IO.Path]::DirectorySeparatorChar
    foreach ($record in $Records) {
        $source = Get-T19CanonicalPath $record.source_path
        $copy = Get-T19CanonicalPath $record.body_copy
        if (-not $copy.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase) -or -not $seen.Add($source) -or -not $SourceMap.ContainsKey($source)) {
            throw 'T19_SOURCE_BODY_SCOPE_DENIED'
        }
        $null = Assert-T19FileIdentity $copy $SourceMap[$source]
    }
}

function Assert-T19ClosedInputs {
    param($Binding, $Admission, $Bodies, [string]$OwnedRoot)
    $sources = Assert-T19ExactIdentityMap $Binding.required_sources $Admission.production_and_test_sources
    $resources = Assert-T19ExactIdentityMap $Binding.required_resources $Admission.runtime_resources
    Assert-T19SourceBodies $sources $Bodies $OwnedRoot
    Assert-T19DirectorySets $Binding.source_directory_scopes $sources
    Assert-T19DirectorySets $Binding.resource_directory_scopes $resources
    $target = Get-T19CanonicalPath $Binding.target_path
    $sourceRoot = Get-T19CanonicalPath $Binding.source_root
    if ($Binding.target_module -cne 'video_creator.application.bundles' -or -not $sources.ContainsKey($target)) { throw 'T19_TARGET_NOT_BOUND' }
    $chain = @(
        @{ module = 'video_creator'; path = Join-Path $sourceRoot 'video_creator/__init__.py' },
        @{ module = 'video_creator.application'; path = Join-Path $sourceRoot 'video_creator/application/__init__.py' },
        @{ module = 'video_creator.application.bundles'; path = Join-Path $sourceRoot 'video_creator/application/bundles.py' }
    )
    if ($Binding.module_chain.Count -ne 3) { throw 'T19_PARENT_PACKAGE_MISSING' }
    for ($index = 0; $index -lt 3; $index++) {
        $path = Get-T19CanonicalPath $chain[$index].path
        if (-not $sources.ContainsKey($path) -or $Binding.module_chain[$index].module -cne $chain[$index].module -or (Get-T19CanonicalPath $Binding.module_chain[$index].path) -ine $path) {
            throw 'T19_PARENT_PACKAGE_MISSING'
        }
    }
    if ((Get-T19CanonicalPath $chain[2].path) -ine $target) { throw 'T19_TARGET_PATH_MISMATCH' }
    if ($Admission.paid_provider_calls_allowed -isnot [bool] -or $Admission.paid_provider_calls_allowed) { throw 'T19_FEE_BOUNDARY_DENIED' }
    return @{ Sources = $sources; Resources = $resources }
}

function Get-T19OwnedSnapshot {
    param([int]$RootPid, [string]$RootCreation)
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $rootProcess = @($processes | Where-Object ProcessId -eq $RootPid)
    if ($rootProcess.Count -eq 0) { return @() }
    if ($rootProcess.Count -ne 1 -or $rootProcess[0].CreationDate.ToUniversalTime().ToString('o') -cne $RootCreation) { throw 'T19_ROOT_PID_IDENTITY_CHANGED' }
    $owned = [System.Collections.Generic.HashSet[int]]::new()
    $null = $owned.Add($RootPid)
    do {
        $changed = $false
        foreach ($process in $processes) {
            if ($owned.Contains([int]$process.ParentProcessId) -and -not $owned.Contains([int]$process.ProcessId)) {
                $null = $owned.Add([int]$process.ProcessId)
                $changed = $true
            }
        }
    } while ($changed)
    return @($processes | Where-Object { $owned.Contains([int]$_.ProcessId) } | ForEach-Object {
        @{ pid = [int]$_.ProcessId; parent = [int]$_.ParentProcessId; creation = $_.CreationDate.ToUniversalTime().ToString('o') }
    })
}

function Stop-T19CapturedTree {
    param($Captured)
    $forced = @()
    # This is bounded captured-CIM supervision, NOT a Job Object containment
    # proof. Unknown identities are never guessed or force-killed.
    foreach ($record in @($Captured | Sort-Object @{ Expression = { $_.pid -eq $_.parent } })) {
        $current = @(Get-CimInstance Win32_Process -Filter "ProcessId=$($record.pid)" -ErrorAction Stop)
        if ($current.Count -eq 0) { continue }
        if ($current.Count -ne 1 -or $current[0].CreationDate.ToUniversalTime().ToString('o') -cne $record.creation -or [int]$current[0].ParentProcessId -ne [int]$record.parent) {
            throw 'T19_CAPTURED_PID_REUSED_NO_FORCE'
        }
        Stop-Process -Id $record.pid -Force -ErrorAction Stop
        $forced += $record.pid
    }
    Start-Sleep -Milliseconds 100
    $remaining = @()
    foreach ($record in $Captured) {
        $current = @(Get-CimInstance Win32_Process -Filter "ProcessId=$($record.pid)" -ErrorAction Stop)
        if ($current.Count -eq 1 -and $current[0].CreationDate.ToUniversalTime().ToString('o') -ceq $record.creation) { $remaining += $record.pid }
    }
    return @{ forced_pids = $forced; remaining_captured_pids = $remaining; verified_captured_terminal = ($remaining.Count -eq 0); scope = 'finite CIM snapshots only; unobserved descendants/TOCTOU are not OS containment' }
}

Export-ModuleMember -Function Read-T19StrictJson, Get-T19CanonicalPath, Assert-T19OwnedWriteTarget, Assert-T19FileIdentity, ConvertTo-T19IdentityMap, Assert-T19ExactIdentityMap, Assert-T19DirectorySets, Assert-T19SourceBodies, Assert-T19ClosedInputs, Get-T19OwnedSnapshot, Stop-T19CapturedTree

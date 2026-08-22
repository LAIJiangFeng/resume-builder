# author: jf
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^(brainstorm|prd|ui|implement|break_loop|quality_gate|submit|archive)\.[a-z][a-z0-9_-]*$')]
    [string]$Hook,

    [string[]]$Tags = @(),

    [string[]]$RequestedPlugins = @(),

    [switch]$Authorized
)

$ErrorActionPreference = 'Stop'

function ConvertTo-NormalizedSet {
    param([string[]]$Values)

    $set = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($value in $Values) {
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            [void]$set.Add($value.Trim().ToLowerInvariant())
        }
    }
    return ,$set
}

function Test-HookCondition {
    param(
        [object]$Condition,
        [System.Collections.Generic.HashSet[string]]$TaskTags,
        [bool]$HasAuthorization
    )

    if ($Condition.requiresAuthorization -eq $true -and -not $HasAuthorization) {
        return $false
    }

    $anyTags = @($Condition.anyTags | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    if ($anyTags.Count -gt 0) {
        $hasAnyTag = $false
        foreach ($tag in $anyTags) {
            if ($TaskTags.Contains([string]$tag)) {
                $hasAnyTag = $true
                break
            }
        }
        if (-not $hasAnyTag) {
            return $false
        }
    }

    $allTags = @($Condition.allTags | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    foreach ($tag in $allTags) {
        if (-not $TaskTags.Contains([string]$tag)) {
            return $false
        }
    }

    return $true
}

$workflowRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $workflowRoot 'lifecycle-plugins.json'
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "未找到生命周期插件配置: $configPath"
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if ($config.author -ne 'jf' -or [int]$config.version -lt 1) {
    throw '生命周期插件配置的 author 或 version 无效。'
}

$knownHooks = ConvertTo-NormalizedSet -Values @($config.hooks | ForEach-Object { $_.id })
if (-not $knownHooks.Contains($Hook)) {
    throw "未注册生命周期 Hook: $Hook"
}

$taskTags = ConvertTo-NormalizedSet -Values $Tags
$requested = ConvertTo-NormalizedSet -Values $RequestedPlugins
$explicitMatches = @()
$automaticMatches = @()

foreach ($plugin in @($config.plugins)) {
    if ($plugin.enabled -ne $true) {
        continue
    }

    $matchingHook = @($plugin.hooks | Where-Object { $_.point -eq $Hook }) | Select-Object -First 1
    if ($null -eq $matchingHook) {
        continue
    }

    $isExplicit = $requested.Contains([string]$plugin.id)
    if ($plugin.activation -eq 'manual' -and -not $isExplicit) {
        continue
    }

    if ($isExplicit) {
        if ($matchingHook.when.requiresAuthorization -eq $true -and -not $Authorized.IsPresent) {
            continue
        }
    }
    elseif (-not (Test-HookCondition -Condition $matchingHook.when -TaskTags $taskTags -HasAuthorization $Authorized.IsPresent)) {
        continue
    }

    $resolvedEntry = $null
    if ($plugin.kind -eq 'skill') {
        if ($plugin.source -eq 'runtime') {
            $resolvedEntry = "runtime://$($plugin.provider)"
        }
        else {
            $entryCandidates = @($plugin.entry) + @($plugin.fallbackEntries)
            foreach ($entryCandidate in $entryCandidates) {
                if ([string]::IsNullOrWhiteSpace($entryCandidate)) {
                    continue
                }
                $absoluteEntry = Join-Path (Split-Path -Parent $workflowRoot) $entryCandidate
                if (Test-Path -LiteralPath $absoluteEntry) {
                    $resolvedEntry = $entryCandidate
                    break
                }
            }
        }
    }

    $match = [pscustomobject]@{
        id = $plugin.id
        kind = $plugin.kind
        provider = $plugin.provider
        source = $plugin.source
        hook = $Hook
        priority = [int]$plugin.priority
        explicit = $isExplicit
        entry = $resolvedEntry
        fallback = $plugin.fallback
        description = $plugin.description
    }

    if ($isExplicit) {
        $explicitMatches += $match
    }
    elseif ($plugin.activation -in @('always', 'conditional')) {
        $automaticMatches += $match
    }
}

$explicitMatches = @($explicitMatches | Sort-Object -Property @{ Expression = 'priority'; Descending = $true }, id)
$automaticMatches = @($automaticMatches | Sort-Object -Property @{ Expression = 'priority'; Descending = $true }, id)
$automaticLimit = [int]$config.selection.maxAutomaticPluginsPerHook
if ($automaticLimit -ge 0) {
    $automaticMatches = @($automaticMatches | Select-Object -First $automaticLimit)
}

$selected = @()
if ($config.selection.explicitPluginsBypassAutomaticLimit -eq $true) {
    $selected = @($explicitMatches)
    $selectedIds = ConvertTo-NormalizedSet -Values @($selected | ForEach-Object { $_.id })
    foreach ($match in $automaticMatches) {
        if (-not $selectedIds.Contains([string]$match.id)) {
            $selected += $match
            [void]$selectedIds.Add([string]$match.id)
        }
    }
}
else {
    $selected = @($explicitMatches + $automaticMatches | Sort-Object -Property @{ Expression = 'priority'; Descending = $true }, id | Select-Object -First $automaticLimit)
}

$selectedIds = ConvertTo-NormalizedSet -Values @($selected | ForEach-Object { $_.id })
$unresolvedRequestedPlugins = @()
foreach ($requestedId in @($requested | Sort-Object)) {
    if ($selectedIds.Contains([string]$requestedId)) {
        continue
    }

    $requestedPlugin = @($config.plugins | Where-Object { $_.id -eq $requestedId }) | Select-Object -First 1
    $reason = 'not_selected'
    if ($null -eq $requestedPlugin) {
        $reason = 'not_registered'
    }
    elseif ($requestedPlugin.enabled -ne $true) {
        $reason = 'disabled'
    }
    else {
        $requestedHook = @($requestedPlugin.hooks | Where-Object { $_.point -eq $Hook }) | Select-Object -First 1
        if ($null -eq $requestedHook) {
            $reason = 'hook_not_supported'
        }
        elseif ($requestedHook.when.requiresAuthorization -eq $true -and -not $Authorized.IsPresent) {
            $reason = 'authorization_required'
        }
    }

    $unresolvedRequestedPlugins += [pscustomobject]@{
        id = $requestedId
        reason = $reason
    }
}

[pscustomobject]@{
    hook = $Hook
    tags = @($taskTags | Sort-Object)
    requestedPlugins = @($requested | Sort-Object)
    authorized = $Authorized.IsPresent
    contextMode = $config.selection.contextMode
    evidenceMode = $config.selection.evidenceMode
    selected = $selected
    unresolvedRequestedPlugins = $unresolvedRequestedPlugins
} | ConvertTo-Json -Depth 10

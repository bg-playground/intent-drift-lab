# Public Intent Drift Lab — Windows demo runner (no WSL / bash required)
$ErrorActionPreference = "Stop"
# PowerShell 7+ otherwise treats python exit 2 (NO-GO) as a terminating error.
$PSNativeCommandUseErrorActionPreference = $false
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force -Path (Join-Path $Root "evidence") | Out-Null

function Resolve-Python {
    foreach ($candidate in @("python", "py")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) { return $candidate }
    }
    throw "Python was not found on PATH. Install Python 3.11+ and retry."
}

$Python = Resolve-Python

function Invoke-DemoRow {
    param(
        [string]$Label,
        [string]$Artifact,
        [string]$Contract,
        [string]$JsonOut,
        [string]$HtmlOut,
        [string]$Expected
    )

    if ($Python -eq "py") {
        & py -3 tools/drift_lab.py --artifact $Artifact --contract $Contract --json-out $JsonOut --html-out $HtmlOut
    } else {
        & python tools/drift_lab.py --artifact $Artifact --contract $Contract --json-out $JsonOut --html-out $HtmlOut
    }
    $code = $LASTEXITCODE
    $decision = "ERROR"
    if ($code -eq 0) { $decision = "GO" }
    elseif ($code -eq 2) { $decision = "NO-GO" }

    $artifactKind = ((Split-Path $Artifact -Leaf) -split "\.")[1]
    "{0,-16} {1,-18} {2,-8} (expected {3}, exit {4})" -f $Label, $artifactKind, $decision, $Expected, $code
    if ($decision -ne $Expected) {
        throw "Demo mismatch for $Label"
    }
}

Write-Output "Fixture          Artifact           Decision"
Write-Output "----------------------------------------------"
Invoke-DemoRow TESLA-FSD-001 artifacts/tesla-fsd.baseline.yaml policies/TESLA-FSD-001.json evidence/tesla-baseline.json evidence/tesla-baseline.html GO
Invoke-DemoRow TESLA-FSD-001 mutations/tesla-fsd.occupant-may-rest.yaml policies/TESLA-FSD-001.json evidence/tesla-mutation.json evidence/tesla-mutation.html "NO-GO"
Invoke-DemoRow SPACEX-SL-001 artifacts/spacex-sl.baseline.yaml policies/SPACEX-SL-001.json evidence/spacex-baseline.json evidence/spacex-baseline.html GO
Invoke-DemoRow SPACEX-SL-001 mutations/spacex-sl.threshold-weakened.yaml policies/SPACEX-SL-001.json evidence/spacex-mutation.json evidence/spacex-mutation.html "NO-GO"
Invoke-DemoRow XAI-GROK-001 artifacts/xai-grok.baseline.yaml policies/XAI-GROK-001.json evidence/xai-baseline.json evidence/xai-baseline.html GO
Invoke-DemoRow XAI-GROK-001 mutations/xai-grok.self-report.yaml policies/XAI-GROK-001.json evidence/xai-mutation.json evidence/xai-mutation.html "NO-GO"
Write-Output "----------------------------------------------"
Write-Output "All six demo rows matched."

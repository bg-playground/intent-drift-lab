#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p evidence

run() {
  local label="$1"
  local artifact="$2"
  local contract="$3"
  local json_out="$4"
  local html_out="$5"
  local expected="$6"
  set +e
  python3 tools/drift_lab.py \
    --artifact "$artifact" \
    --contract "$contract" \
    --json-out "$json_out" \
    --html-out "$html_out"
  local code=$?
  set -e
  local decision="ERROR"
  if [[ "$code" -eq 0 ]]; then
    decision="GO"
  elif [[ "$code" -eq 2 ]]; then
    decision="NO-GO"
  fi
  printf '%-16s %-10s %-8s (expected %s, exit %s)\n' "$label" "$(basename "$artifact" | cut -d. -f2)" "$decision" "$expected" "$code"
  if [[ "$decision" != "$expected" ]]; then
    echo "Demo mismatch for $label" >&2
    exit 1
  fi
}

echo "Fixture          Artifact   Decision"
echo "----------------------------------------"
run TESLA-FSD-001 artifacts/tesla-fsd.baseline.yaml policies/TESLA-FSD-001.json evidence/tesla-baseline.json evidence/tesla-baseline.html GO
run TESLA-FSD-001 mutations/tesla-fsd.occupant-may-rest.yaml policies/TESLA-FSD-001.json evidence/tesla-mutation.json evidence/tesla-mutation.html NO-GO
run SPACEX-SL-001 artifacts/spacex-sl.baseline.yaml policies/SPACEX-SL-001.json evidence/spacex-baseline.json evidence/spacex-baseline.html GO
run SPACEX-SL-001 mutations/spacex-sl.threshold-weakened.yaml policies/SPACEX-SL-001.json evidence/spacex-mutation.json evidence/spacex-mutation.html NO-GO
run XAI-GROK-001 artifacts/xai-grok.baseline.yaml policies/XAI-GROK-001.json evidence/xai-baseline.json evidence/xai-baseline.html GO
run XAI-GROK-001 mutations/xai-grok.self-report.yaml policies/XAI-GROK-001.json evidence/xai-mutation.json evidence/xai-mutation.html NO-GO
echo "----------------------------------------"
echo "All six demo rows matched."

# Public Intent Drift Lab

> Test whether a public-style product claim still means what it used to mean — not whether the document still parses.

This repository is an independent demonstration of intent-aware testing. It is not affiliated with Tesla, SpaceX, xAI, or X. Fixtures are lab analogs. Reports are not product certifications, safety cases, or launch-readiness evidence.

Sister lab: [salesforce-change-impact-lab](https://github.com/bg-playground/salesforce-change-impact-lab) · Methodology: [BGSTM](https://github.com/bg-playground/BGSTM)

## Why this exists

Typical demos ask whether a page still loads, a spec still parses, or a model still sounds fluent. Those checks can stay green after the operating rule silently moved.

Public Intent Drift Lab freezes a claim as a contract, reads a current artifact, and issues a deterministic **GO / NO-GO** with BGSTM-style evidence.

```text
Frozen public intent
        │
        ▼
Current artifact ──► narrow extractor
        │                    │
        │                    ▼
        │              independent oracle
        │                    │
        ├─────────────► boundary cases
        │                    │
        ▼                    ▼
happy-path parse        evidence + decision
still green             GO / NO-GO
```

The implementation does not grade itself. The policy contract is the oracle.

## 60-second demo

Run these from the repo root (`intent-drift-lab`), not from `evidence/`.

macOS / Linux:

```bash
git clone https://github.com/bg-playground/intent-drift-lab.git
cd intent-drift-lab
python3 -m unittest tests.test_drift_lab -v
bash scripts/run-demo.sh
```

Windows PowerShell (no WSL or bash required):

```powershell
git clone https://github.com/bg-playground/intent-drift-lab.git
cd intent-drift-lab
python -m unittest tests.test_drift_lab -v
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1
```

No third-party packages. No API keys. No network.

Expected demo table:

| Fixture | Artifact | Decision |
|---|---|---|
| TESLA-FSD-001 | baseline | **GO** |
| TESLA-FSD-001 | mutant | **NO-GO** |
| SPACEX-SL-001 | baseline | **GO** |
| SPACEX-SL-001 | mutant | **NO-GO** |
| XAI-GROK-001 | baseline | **GO** |
| XAI-GROK-001 | mutant | **NO-GO** |

The mutant command exits `2`. A missing file or unknown rule kind exits `1` and never emits GO.

## The three fixtures

| ID | Drift type | What stays green | What the oracle catches |
|---|---|---|---|
| `TESLA-FSD-001` | Qualifier | Product name is still `FSD` | `supervised` drifted to `occupant_may_rest` |
| `SPACEX-SL-001` | Threshold | Service name is still `AviationLink` | Availability floor and latency ceiling weakened |
| `XAI-GROK-001` | Affiliation | Assistant name is still `Grok` | Decision owner drifted to model self-report |

These are lab analogs. They use recognizable product vocabulary so the failure mode is obvious. They are not copies of current official policy.

## One fixture by hand

```bash
python3 tools/drift_lab.py --artifact artifacts/tesla-fsd.baseline.yaml --contract policies/TESLA-FSD-001.json --json-out evidence/tesla-baseline.json --html-out evidence/tesla-baseline.html
python3 tools/drift_lab.py --artifact mutations/tesla-fsd.occupant-may-rest.yaml --contract policies/TESLA-FSD-001.json --json-out evidence/tesla-mutation.json --html-out evidence/tesla-mutation.html
```

On Windows, use `python` instead of `python3` if that is the command on your PATH.

## BGSTM mapping

| Phase | Lab artifact |
|---|---|
| 1. Test Planning | `policies/*.json` freezes intent and risk |
| 2. Test Case Development | Boundary cases generated from the contract |
| 3. Environment Preparation | Offline CPython, stdlib only |
| 4. Test Execution | YAML extraction + independent oracle |
| 5. Test Results Analysis | Alignment and mismatch count |
| 6. Test Results Reporting | JSON + HTML + exit code |

## Repository map

```text
policies/     Frozen intent contracts
artifacts/    Baseline public-style artifacts
mutations/    Valid artifacts with silent semantic drift
tools/        Deterministic evidence runner
tests/        Offline regression tests for the lab itself
docs/         Architecture, BGSTM mapping, disclaimer
evidence/     Generated reports (local only)
```

## What v1 is not

No live X fetch, Tesla Fleet API, Starlink telemetry, or Grok API. No partnership implication. No mission-control UI. No TRUE/FALSE fact-check swarm.

## License

MIT.

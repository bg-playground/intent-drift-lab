# BGSTM mapping

Public Intent Drift Lab applies the six BGSTM phases. It does not add a seventh phase.

| Phase | Purpose | Lab artifact |
|---|---|---|
| 1. Test Planning | Freeze scope, risk, and intent | `policies/*.json` |
| 2. Test Case Development | Design traceable cases | Boundary cases generated from each rule |
| 3. Test Environment Preparation | Prepare tools and data | Offline CPython; committed YAML fixtures |
| 4. Test Execution | Run tests and collect evidence | `tools/drift_lab.py` |
| 5. Test Results Analysis | Interpret mismatches | `aligned`, `mismatch_count`, case table |
| 6. Test Results Reporting | Support a release decision | JSON, HTML, exit `0` / `2` |

The requirement ID is the traceability key. It appears on the contract, the report, and the HTML title.

Related methodology: [BGSTM](https://github.com/bg-playground/BGSTM).

#!/usr/bin/env python3
"""Deterministic public-intent vs artifact evidence runner."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

DISCLAIMER = (
    "This repository is an independent demonstration of intent-aware testing. "
    "It is not affiliated with Tesla, SpaceX, xAI, or X. Fixtures are lab analogs. "
    "Reports are not product certifications, safety cases, or launch-readiness evidence."
)

SUPPORTED_KINDS = {"required_enum", "numeric_threshold", "required_flag"}


class LabError(ValueError):
    """Hard failure: do not emit GO."""


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LabError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in value or "e" in lowered:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_simple_yaml(path: Path) -> dict[str, Any]:
    """Stdlib subset reader: `key: value` lines, `#` comments, no nesting."""
    if not path.is_file():
        raise LabError(f"Missing file: {path}")
    data: dict[str, Any] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if ":" not in line:
            raise LabError(f"{path}:{line_no}: expected 'key: value'")
        key, rest = line.split(":", 1)
        key = key.strip()
        if not key or key.startswith(" ") or " " in key:
            raise LabError(f"{path}:{line_no}: unsupported key '{key}'")
        data[key] = parse_scalar(rest)
    return data


def rules_from_contract(contract: dict[str, Any]) -> list[dict[str, Any]]:
    rule = contract.get("rule")
    if not isinstance(rule, dict):
        raise LabError("Contract is missing a rule object")
    bundled = [rule, *contract.get("supporting_rules", [])]
    out: list[dict[str, Any]] = []
    for item in bundled:
        if not isinstance(item, dict):
            raise LabError("Each rule must be an object")
        kind = item.get("kind")
        if kind not in SUPPORTED_KINDS:
            raise LabError(f"Unknown rule kind: {kind}")
        if "path" not in item:
            raise LabError("Rule is missing path")
        out.append(item)
    return out


def require_path(artifact: dict[str, Any], path: str) -> Any:
    if path not in artifact:
        raise LabError(f"Missing required artifact path: {path}")
    return artifact[path]


def as_number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LabError(f"Non-numeric threshold at {path}: {value!r}")
    return float(value)


def rule_aligned(rule: dict[str, Any], observed: Any) -> bool:
    kind = rule["kind"]
    if kind == "required_enum":
        allowed = list(rule.get("allowed") or [rule["expected"]])
        forbidden = list(rule.get("forbidden") or [])
        return observed in allowed and observed not in forbidden and observed == rule["expected"]
    if kind == "required_flag":
        return bool(observed) is bool(rule["expected"])
    operator = rule.get("operator")
    number = as_number(observed, rule["path"])
    expected = as_number(rule["expected"], rule["path"])
    if operator == ">=":
        return number >= expected
    if operator == "<=":
        return number <= expected
    raise LabError(f"Unsupported numeric operator: {operator}")


def happy_path_passed(contract: dict[str, Any], artifact: dict[str, Any]) -> bool:
    spec = contract.get("happy_path") or {}
    path = spec.get("path")
    if not path:
        return True
    if path not in artifact:
        return False
    return artifact[path] == spec.get("expected")


def evaluate_rules(rules: list[dict[str, Any]], artifact: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rule in rules:
        observed = require_path(artifact, rule["path"])
        if rule["kind"] == "numeric_threshold":
            observed = as_number(observed, rule["path"])
        matches = rule_aligned(rule, observed)
        rows.append(
            {
                "path": rule["path"],
                "kind": rule["kind"],
                "operator": rule.get("operator", "eq"),
                "expected": rule["expected"],
                "observed": observed,
                "intent_requires": describe_intent(rule),
                "artifact_provides": observed,
                "matches_intent": matches,
                "actual_artifact": True,
            }
        )
    return rows


def describe_intent(rule: dict[str, Any]) -> str:
    kind = rule["kind"]
    path = rule["path"]
    if kind == "required_enum":
        return f"{path} == {rule['expected']}"
    if kind == "required_flag":
        return f"{path} is {rule['expected']}"
    return f"{path} {rule['operator']} {rule['expected']}"


def boundary_cases(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hypothetical values that document the frozen boundary."""
    rows: list[dict[str, Any]] = []
    for rule in rules:
        kind = rule["kind"]
        path = rule["path"]
        if kind == "required_enum":
            variants = [rule["expected"], *list(rule.get("forbidden") or [])]
            seen: set[Any] = set()
            for value in variants:
                if value in seen:
                    continue
                seen.add(value)
                rows.append(case_row(rule, value, actual=False))
        elif kind == "required_flag":
            rows.append(case_row(rule, rule["expected"], actual=False))
            rows.append(case_row(rule, not bool(rule["expected"]), actual=False))
        else:
            expected = as_number(rule["expected"], path)
            step = 0.01 if expected < 10 or expected != int(expected) else 1
            if rule["operator"] == ">=":
                variants = [expected, expected + step, expected - step]
            else:
                variants = [expected, expected - step, expected + step]
            for value in variants:
                rows.append(case_row(rule, round(value, 4), actual=False))
    return rows


def case_row(rule: dict[str, Any], value: Any, actual: bool) -> dict[str, Any]:
    matches = rule_aligned(rule, value)
    return {
        "path": rule["path"],
        "kind": rule["kind"],
        "operator": rule.get("operator", "eq"),
        "expected": rule["expected"],
        "observed": value,
        "intent_requires": describe_intent(rule),
        "artifact_provides": value,
        "matches_intent": matches,
        "actual_artifact": actual,
    }


def analyze(artifact_path: Path, contract_path: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    artifact = load_simple_yaml(artifact_path)
    rules = rules_from_contract(contract)
    actual_rows = evaluate_rules(rules, artifact)
    mismatch_count = sum(1 for row in actual_rows if not row["matches_intent"])
    aligned = mismatch_count == 0
    cases = actual_rows + boundary_cases(rules)
    decision = "GO" if aligned else "NO-GO"
    primary = rules[0]
    observed_primary = next(row["observed"] for row in actual_rows if row["path"] == primary["path"])
    reason = (
        "Artifact matches the frozen public intent and every required supporting rule."
        if decision == "GO"
        else "Artifact is still valid on the happy path, but at least one frozen intent rule drifted."
    )
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_id": contract["requirement_id"],
        "title": contract["title"],
        "domain": contract["domain"],
        "risk": contract["risk"],
        "contract_path": str(contract_path).replace("\\", "/"),
        "artifact_path": str(artifact_path).replace("\\", "/"),
        "rule_kind": primary["kind"],
        "path": primary["path"],
        "expected": primary["expected"],
        "observed": observed_primary,
        "aligned": aligned,
        "happy_path_passed": happy_path_passed(contract, artifact),
        "case_count": len(cases),
        "mismatch_count": mismatch_count,
        "cases": cases,
        "release_decision": decision,
        "decision_reason": reason,
        "disclaimer": DISCLAIMER,
        "artifact": artifact,
        "bgstm_trace": {
            "phase_1_planning": contract["bgstm"]["planning_risk"],
            "phase_2_test_design": "Generated boundary cases from frozen intent",
            "phase_3_environment": "Offline stdlib runner; no credentials",
            "phase_4_execution": "Independent YAML oracle",
            "phase_5_analysis": f"{mismatch_count} semantic rule mismatch(es)",
            "phase_6_reporting": decision,
            "traceability_id": contract["bgstm"]["traceability_id"],
        },
    }


def render_html(report: dict[str, Any]) -> str:
    cls = "go" if report["release_decision"] == "GO" else "nogo"
    rows = []
    for case in report["cases"]:
        marker = "actual" if case["actual_artifact"] else "boundary"
        match = "✓" if case["matches_intent"] else "✕"
        rows.append(
            "<tr>"
            f"<td>{escape(str(case['path']))}</td>"
            f"<td>{escape(str(case['artifact_provides']))}</td>"
            f"<td>{escape(str(case['intent_requires']))}</td>"
            f"<td>{marker}</td>"
            f"<td>{match}</td>"
            "</tr>"
        )
    artifact_block = "\n".join(
        f"{key}: {report['artifact'][key]}" for key in report["artifact"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(report['requirement_id'])} — Public Intent Drift Lab</title>
  <style>
    :root {{ font-family: Inter, system-ui, sans-serif; color: #172033; background: #f6f8fb; }}
    main {{ max-width: 1050px; margin: auto; padding: 40px 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }}
    .card {{ background: white; border: 1px solid #dfe5ec; border-radius: 14px; padding: 18px; margin-top: 20px; }}
    .value {{ font-size: 28px; font-weight: 750; }}
    .go .value {{ color: #2e844a; }}
    .nogo .value {{ color: #ba0517; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ padding: 12px; border-bottom: 1px solid #edf0f4; text-align: left; }}
    th {{ background: #eef3f8; }}
    pre {{ white-space: pre-wrap; background: #101828; color: #eef4ff; padding: 18px; border-radius: 14px; }}
    .disclaimer {{ font-size: 14px; color: #475467; }}
  </style>
</head>
<body>
<main>
  <p>Public Intent Drift Lab · {escape(report['requirement_id'])}</p>
  <h1>{escape(report['title'])}</h1>
  <div class="grid">
    <div class="card {cls}"><small>Release decision</small><div class="value">{report['release_decision']}</div></div>
    <div class="card"><small>Expected</small><div class="value">{escape(str(report['expected']))}</div></div>
    <div class="card"><small>Observed</small><div class="value">{escape(str(report['observed']))}</div></div>
    <div class="card"><small>Semantic mismatches</small><div class="value">{report['mismatch_count']}</div></div>
  </div>
  <div class="card">
    <h2>Decision rationale</h2>
    <p>{escape(report['decision_reason'])}</p>
    <p>Happy path passed: {'yes' if report['happy_path_passed'] else 'no'}</p>
  </div>
  <h2>Evidence</h2>
  <table>
    <thead><tr><th>Path</th><th>Value</th><th>Intent</th><th>Kind</th><th>Match</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <h2>Extracted artifact</h2>
  <pre>{escape(artifact_block)}</pre>
  <div class="card disclaimer"><p>{escape(report['disclaimer'])}</p></div>
</main>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare a frozen intent contract to a public-style artifact.")
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--html-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze(args.artifact, args.contract)
    except LabError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: value for key, value in report.items() if key != "artifact"}
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.html_out:
        args.html_out.parent.mkdir(parents=True, exist_ok=True)
        args.html_out.write_text(render_html(report), encoding="utf-8")
    print(
        f"{report['requirement_id']}: {report['release_decision']} | "
        f"{report['path']} expected={report['expected']} observed={report['observed']} | "
        f"mismatches={report['mismatch_count']} happy_path={report['happy_path_passed']}"
    )
    return 0 if report["release_decision"] == "GO" else 2


if __name__ == "__main__":
    sys.exit(main())

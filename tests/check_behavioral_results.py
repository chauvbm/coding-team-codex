"""Score independent scenario decisions; this does not execute or enforce the skill."""

import argparse
import json
from pathlib import Path


def check_results(cases, responses):
    """Return decision-level failures, including missing or duplicate evaluations."""
    failures = []
    expected = {case["id"]: case for case in cases}
    seen = set()
    required = {
        "id": str, "action": str, "gate": str, "operating_state": str,
        "can_write_affected": bool, "ask_user": bool, "reset_counters": bool,
        "repeat_arguments": bool, "rationale": str,
    }
    enums = {
        "gate": {"PASS", "HOLD", "NOT_REQUIRED"},
        "operating_state": {"ACTIVE", "EVIDENCE_MODE", "STOP_HOLD", "PASS", "PAUSED"},
        "action": {"independent_review", "organize_correction", "targeted_reassessment",
                   "evidence_action", "plan_repair", "repair_verify", "hold", "schedule_work",
                   "ownership_handoff", "verify_integrated", "direct_work", "pause",
                   "await_review", "implement", "complete"},
    }
    for result in responses:
        if not isinstance(result, dict) or not isinstance(result.get("id"), str):
            failures.append("Response must be an object with a string id")
            continue
        case_id = result["id"]
        if case_id in seen:
            failures.append(f"{case_id}: duplicate response")
            continue
        seen.add(case_id)
        if case_id not in expected:
            failures.append(f"{case_id}: unknown case")
            continue
        for field, kind in required.items():
            if type(result.get(field)) is not kind:
                failures.append(f"{case_id}: missing/invalid {field}")
        for field, choices in enums.items():
            if type(result.get(field)) is not str or result[field] not in choices:
                failures.append(f"{case_id}: invalid {field}")
        if type(result.get("rationale")) is str and not result["rationale"].strip():
            failures.append(f"{case_id}: empty rationale")
        for invariant in ("reset_counters", "repeat_arguments"):
            if result.get(invariant) is not False:
                failures.append(f"{case_id}: shared invariant {invariant} must be false")
        if (result.get("gate") == "HOLD" or result.get("operating_state") in ("STOP_HOLD", "PAUSED")):
            if result.get("can_write_affected") is not False:
                failures.append(f"{case_id}: affected writes cannot proceed during hold/pause")
        for operation, checks in expected[case_id]["checks"].items():
            for field, target in checks.items():
                actual = result.get(field)
                if operation == "equals":
                    passed = type(actual) is type(target) and actual == target
                elif operation == "one_of":
                    passed = any(type(actual) is type(item) and actual == item for item in target)
                elif operation == "lte":
                    passed = type(actual) in (int, float) and 0 <= actual <= target
                else:
                    raise ValueError(f"Unknown check operation: {operation}")
                if not passed:
                    failures.append(f"{case_id}: {field}={actual!r}; expected {operation} {target!r}")
    failures.extend(f"{case_id}: missing response" for case_id in sorted(expected.keys() - seen))
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("responses", nargs="+", type=Path, help="Independent evaluator JSON arrays")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("behavioral_cases.json"))
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8-sig"))["cases"]
    responses = []
    for path in args.responses:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            parser.error(f"{path}: expected a JSON array")
        responses.extend(data)
    failures = check_results(cases, responses)
    print(json.dumps({"cases": len(cases), "responses": len(responses), "passed": not failures,
                      "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    name: str
    status: str
    severity: str
    details: str


def read_text(path: str) -> str:
    file_path = ROOT / path
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def contains(path: str, expected: str) -> bool:
    return expected in read_text(path)


def contains_any(path: str, expected_values: tuple[str, ...]) -> bool:
    text = read_text(path).lower()
    return all(value.lower() in text for value in expected_values)


def check(name: str, condition: bool, details: str, severity: str = "critical") -> CheckResult:
    return CheckResult(
        name=name,
        status="pass" if condition else "fail",
        severity=severity,
        details=details,
    )


def run_checks() -> list[CheckResult]:
    ci_text = read_text(".github/workflows/ci.yml")

    return [
        check(
            "metric_contract_exists",
            exists("docs/metric_contract_arr.md"),
            "docs/metric_contract_arr.md",
        ),
        check(
            "business_owner_declared",
            contains("docs/metric_contract_arr.md", "Business owner:** RevOps"),
            "Metric contract declares RevOps as business owner.",
        ),
        check(
            "technical_owner_declared",
            contains("docs/metric_contract_arr.md", "Technical owner:** Data"),
            "Metric contract declares Data as technical owner.",
        ),
        check(
            "certified_grain_documented",
            contains(
                "docs/metric_contract_arr.md",
                "snapshot_date x account_id x subscription_id x product_family",
            )
            or contains(
                "docs/metric_contract_arr.md",
                "snapshot_date × account_id × subscription_id × product_family",
            ),
            "Metric contract documents the certified output grain.",
        ),
        check(
            "invalid_uses_documented",
            contains_any("docs/metric_contract_arr.md", ("invalid uses", "gaap revenue")),
            "Metric contract documents invalid uses.",
        ),
        check(
            "change_process_documented",
            contains_any("docs/metric_contract_arr.md", ("change process", "approval")),
            "Metric contract documents the change process.",
        ),
        check(
            "semantic_model_exists",
            exists("models/semantic/sem_arr.yml"),
            "models/semantic/sem_arr.yml",
        ),
        check(
            "data_quality_summary_exists",
            exists("models/data_quality/dq_arr__summary.sql"),
            "models/data_quality/dq_arr__summary.sql",
        ),
        check(
            "expected_arr_fixture_exists",
            exists("seeds/expected_ending_arr.csv"),
            "seeds/expected_ending_arr.csv",
        ),
        check(
            "critical_business_tests_exist",
            exists("tests/assert_ending_arr_expected_totals.sql")
            and exists("tests/assert_arr_movements_expected.sql"),
            "Expected ARR and movement singular tests exist.",
        ),
        check(
            "ci_runs_semantic_validation",
            "make semantic-validate" in ci_text,
            "CI runs semantic contract validation.",
        ),
        check(
            "ci_runs_governance_validation",
            "make governance-check" in ci_text,
            "CI runs governance quality gate.",
        ),
    ]


def summarize(results: list[CheckResult]) -> dict:
    failed = [result for result in results if result.status != "pass"]
    return {
        "status": "fail" if failed else "pass",
        "score": len(results) - len(failed),
        "max_score": len(results),
        "checks": [asdict(result) for result in results],
    }


def print_human(summary: dict) -> None:
    status = "PASSED" if summary["status"] == "pass" else "FAILED"
    print(f"Governance quality gate: {status}")
    print()

    for result in summary["checks"]:
        marker = "[x]" if result["status"] == "pass" else "[ ]"
        print(f"{marker} {result['name']}: {result['details']}")

    print()
    print(f"Score: {summary['score']}/{summary['max_score']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate governed ARR project controls.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    summary = summarize(run_checks())
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_human(summary)

    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

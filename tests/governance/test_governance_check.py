import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "governance"))

import governance_check as gate
from manifests import (
    lending_fact,
    manifest_from,
    missing_owner_manifest,
    not_null_test,
    tests_for_lending as lending_column_tests,
    unique_test,
)

POLICY = gate.load_yaml(ROOT / "governance" / "policy.yml")
EXCEPTIONS = gate.validate_exceptions(gate.load_yaml(ROOT / "governance" / "exceptions.yml"), POLICY)
TODAY = date(2026, 11, 24)


def failures(manifest, exceptions=None, today=TODAY):
    summary = gate.summarize(gate.evaluate(manifest, POLICY, exceptions or [], today))
    return [
        (check["rule_id"], check["node"], check["details"])
        for check in summary["checks"]
        if check["status"] == "fail"
    ]


def statuses(manifest, exceptions=None, today=TODAY):
    summary = gate.summarize(gate.evaluate(manifest, POLICY, exceptions or [], today))
    return {(check["rule_id"], check["node"]): check["status"] for check in summary["checks"]}


def test_policy_has_at_least_ten_rules_and_conventions_name_them():
    rules = [rule["id"] for rule in POLICY["rules"]]
    assert len(rules) >= 10
    conventions = (ROOT / "docs" / "architecture" / "conventions.md").read_text(encoding="utf-8")
    missing = [rule_id for rule_id in rules if rule_id not in conventions]
    assert missing == []


def test_policy_groups_match_dbt_group_properties():
    groups = yaml.safe_load((ROOT / "models" / "_groups.yml").read_text(encoding="utf-8"))
    declared = [group["name"] for group in groups["groups"]]
    assert declared == POLICY["groups"]


def test_gate_source_does_not_special_case_a_product():
    source = (ROOT / "scripts" / "governance_check.py").read_text(encoding="utf-8")
    for token in ("lending", "fct_arr", "fct_loan", "salesforce"):
        assert token not in source


def test_lending_shaped_public_model_passes_with_metadata_only():
    model = lending_fact()
    summary = gate.summarize(
        gate.evaluate(manifest_from([model], lending_column_tests()), POLICY, [], TODAY)
    )
    assert summary["status"] == "pass", failures(manifest_from([model], lending_column_tests()))
    rule_ids = {check["rule_id"] for check in summary["checks"] if check["node"] == "fct_loan_month_end"}
    assert len(rule_ids) >= 10


def test_missing_owner_fails_own_01_only():
    manifest = missing_owner_manifest()
    found = failures(manifest)
    assert found == [("OWN-01", "fct_arr_snapshot", "meta.owner is missing")]
    summary = gate.summarize(gate.evaluate(manifest, POLICY, [], TODAY))
    assert summary["status"] == "fail"
    assert any(check["name"] == "OWN-01 fct_arr_snapshot" for check in summary["checks"])


def test_unexempted_naming_violation_fails_nam_01():
    model = lending_fact(name="arr_snapshot")
    model["original_file_path"] = "models/marts/revenue/arr_snapshot.sql"
    found = [item for item in failures(manifest_from([model], lending_column_tests("arr_snapshot"))) if item[0] == "NAM-01"]
    assert found
    assert found[0][1] == "arr_snapshot"


def test_active_naming_exception_exempts_the_rule():
    model = lending_fact(name="metricflow_time_spine")
    model["original_file_path"] = "models/marts/core/metricflow_time_spine.sql"
    model["meta"] = {
        "owner": "Data",
        "business_owner": "Data",
        "tier": "supporting",
        "grain": "date_day",
        "freshness_sla": "lab: daily spine",
        "primary_key": ["date_day"],
    }
    model["columns"] = {
        "date_day": {"name": "date_day", "data_type": "date", "description": "Day"},
    }
    tests = [not_null_test("metricflow_time_spine", "date_day"), unique_test("metricflow_time_spine", "date_day")]
    state = statuses(manifest_from([model], tests), EXCEPTIONS)
    assert state[("NAM-01", "metricflow_time_spine")] == "exempt"


def test_expired_exception_does_not_suppress_and_fails_exc_01():
    model = lending_fact()
    model["columns"]["outstanding_principal_minor"]["data_type"] = "decimal(18,2)"
    expired = [
        {
            "rule": "MNY-02",
            "model": "fct_loan_month_end",
            "reason": "old decimal exception",
            "expires_on": date(2026, 1, 1),
            "owner": "Data",
            "require_present": True,
        }
    ]
    state = statuses(manifest_from([model], lending_column_tests()), expired, TODAY)
    assert state[("MNY-02", "fct_loan_month_end")] == "fail"
    assert state[("EXC-01", "fct_loan_month_end")] == "fail"


def test_decimal_money_without_exception_fails_mny_02_and_missing_currency_fails_mny_01():
    model = lending_fact()
    model["columns"]["outstanding_principal_minor"]["data_type"] = "decimal(18,2)"
    del model["columns"]["currency_code"]
    tests = [test for test in lending_column_tests() if test.get("column_name") != "currency_code"]
    found = {(rule, node) for rule, node, _details in failures(manifest_from([model], tests))}
    assert ("MNY-02", "fct_loan_month_end") in found
    assert ("MNY-01", "fct_loan_month_end") in found


def test_private_staging_does_not_require_a_public_contract():
    model = {
        "resource_type": "model",
        "package_name": "arr_semantic_layer_lab",
        "unique_id": "model.arr_semantic_layer_lab.stg_lending__loans",
        "name": "stg_lending__loans",
        "original_file_path": "models/staging/lending/stg_lending__loans.sql",
        "description": "Staged loans.",
        "access": "private",
        "group": "lending",
        "meta": {"owner": "Data"},
        "columns": {
            "loan_id": {"name": "loan_id", "description": "Loan", "data_type": "varchar"},
            "recorded_at": {"name": "recorded_at", "description": "Record time", "data_type": "timestamp"},
        },
    }
    state = statuses(manifest_from([model]))
    assert state[("CTR-01", "stg_lending__loans")] == "pass"
    assert state[("ACC-01", "stg_lending__loans")] == "pass"
    assert state[("GRN-01", "stg_lending__loans")] == "pass"


def test_private_model_with_public_access_fails_acc_01():
    model = {
        "resource_type": "model",
        "package_name": "arr_semantic_layer_lab",
        "unique_id": "model.arr_semantic_layer_lab.stg_lending__loans",
        "name": "stg_lending__loans",
        "original_file_path": "models/staging/lending/stg_lending__loans.sql",
        "description": "Staged loans.",
        "access": "public",
        "group": "lending",
        "contract": {"enforced": True},
        "meta": {"owner": "Data"},
        "columns": {"loan_id": {"name": "loan_id", "data_type": "varchar", "description": "Loan"}},
    }
    found = [item for item in failures(manifest_from([model], [not_null_test("stg_lending__loans", "loan_id")])) if item[0] == "ACC-01"]
    assert found and found[0][1] == "stg_lending__loans"


def test_country_code_without_iso_meta_fails_geo_01():
    model = lending_fact()
    model["columns"]["country_code"]["meta"] = {}
    found = [item for item in failures(manifest_from([model], lending_column_tests())) if item[0] == "GEO-01"]
    assert found


def test_status_column_without_accepted_values_fails_sts_01():
    model = lending_fact()
    tests = [test for test in lending_column_tests() if (test.get("test_metadata") or {}).get("name") != "accepted_values"]
    found = [item for item in failures(manifest_from([model], tests)) if item[0] == "STS-01"]
    assert found


def test_absent_optional_exception_does_not_fail_when_model_is_disabled_out_of_manifest():
    model = lending_fact()
    state = statuses(manifest_from([model], lending_column_tests()), EXCEPTIONS)
    assert ("EXC-01", "revenue_metrics") not in state or state[("EXC-01", "revenue_metrics")] != "fail"
    assert ("EXC-01", "fct_arr_snapshot") in {
        key for key, status in state.items() if status == "fail"
    }


def test_cli_exits_non_zero_for_the_missing_owner_fixture(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(missing_owner_manifest()), encoding="utf-8")
    exceptions_path = tmp_path / "exceptions.yml"
    exceptions_path.write_text("version: 1\nexceptions: []\n", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "governance_check.py"),
            "--manifest",
            str(manifest_path),
            "--policy",
            str(ROOT / "governance" / "policy.yml"),
            "--exceptions",
            str(exceptions_path),
            "--today",
            "2026-11-24",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "OWN-01 fct_arr_snapshot" in completed.stdout


def test_current_manifest_passes_when_dbt_has_built_it():
    manifest_path = ROOT / "target" / "manifest.json"
    if not manifest_path.exists():
        pytest.skip("target/manifest.json is produced by dbt parse or make build")
    summary = gate.run_from_files(manifest_path, ROOT / "governance" / "policy.yml", ROOT / "governance" / "exceptions.yml", TODAY)
    assert summary["status"] == "pass", [
        check for check in summary["checks"] if check["status"] == "fail"
    ]
    snapshot_rules = {check["rule_id"] for check in summary["checks"] if check["node"] == "fct_arr_snapshot"}
    assert len(snapshot_rules) >= 10

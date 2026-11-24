"""Policy gate over a dbt manifest.

Reads governance/policy.yml and governance/exceptions.yml and checks every
enabled project model in target/manifest.json. Rule kinds are generic. A new
product passes by setting group, access, contract, tests, and meta — not by
editing this file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "target" / "manifest.json"
DEFAULT_POLICY = ROOT / "governance" / "policy.yml"
DEFAULT_EXCEPTIONS = ROOT / "governance" / "exceptions.yml"

RULE_KINDS = {
    "name_prefix",
    "known_layer",
    "group_allowed",
    "access_matches_layer",
    "required_meta",
    "primary_key",
    "key_role",
    "contract",
    "currency_column",
    "money_type",
    "temporal_type",
    "accepted_values",
    "column_meta",
    "description",
    "grain_test",
}


@dataclass
class CheckResult:
    rule_id: str
    node: str
    status: str
    severity: str
    details: str

    @property
    def name(self) -> str:
        return f"{self.rule_id} {self.node}".strip()


def as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def type_base(data_type: str | None) -> str:
    if not data_type:
        return ""
    return str(data_type).strip().lower().split("(", 1)[0].strip()


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Governance file not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise SystemExit(f"{path} must be a YAML mapping.")
    return loaded


def validate_policy(policy: dict) -> None:
    if policy.get("version") != 1:
        raise SystemExit("governance/policy.yml version must be 1.")
    groups = policy.get("groups")
    if not isinstance(groups, list) or not groups:
        raise SystemExit("policy.yml groups must be a non-empty list.")
    layers = policy.get("layers")
    if not isinstance(layers, list) or not layers:
        raise SystemExit("policy.yml layers must be a non-empty list.")
    for layer in layers:
        for key in ("name", "path_prefix", "name_prefixes", "access", "contract"):
            if key not in layer:
                raise SystemExit(f"Layer {layer.get('name', '?')} is missing {key}.")
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        raise SystemExit("policy.yml rules must be a non-empty list.")
    seen = set()
    for rule in rules:
        rule_id = rule.get("id")
        kind = rule.get("kind")
        if not rule_id or not kind:
            raise SystemExit(f"Every rule needs id and kind: {rule}")
        if rule_id in seen:
            raise SystemExit(f"Duplicate rule id {rule_id}.")
        seen.add(rule_id)
        if kind not in RULE_KINDS:
            raise SystemExit(f"Unknown rule kind {kind} on {rule_id}.")


def validate_exceptions(exceptions: dict, policy: dict) -> list[dict]:
    if exceptions.get("version") != 1:
        raise SystemExit("governance/exceptions.yml version must be 1.")
    entries = exceptions.get("exceptions") or []
    if not isinstance(entries, list):
        raise SystemExit("exceptions.yml exceptions must be a list.")
    known_rules = {rule["id"] for rule in policy["rules"]}
    required = ("rule", "model", "reason", "expires_on", "owner")
    cleaned = []
    for entry in entries:
        missing = [key for key in required if not entry.get(key)]
        if missing:
            raise SystemExit(f"Exception is missing {missing}: {entry}")
        if entry["rule"] not in known_rules:
            raise SystemExit(f"Exception rule {entry['rule']} is not in policy.yml.")
        cleaned.append(
            {
                "rule": entry["rule"],
                "model": entry["model"],
                "reason": " ".join(str(entry["reason"]).split()),
                "expires_on": as_date(entry["expires_on"]),
                "owner": str(entry["owner"]).strip(),
                "require_present": bool(entry.get("require_present", True)),
            }
        )
    return cleaned


def model_nodes(manifest: dict) -> list[dict]:
    project = (manifest.get("metadata") or {}).get("project_name")
    selected = []
    for node in manifest.get("nodes", {}).values():
        if node.get("resource_type") != "model":
            continue
        if node.get("config", {}).get("enabled") is False:
            continue
        package = node.get("package_name")
        if project and package and package != project:
            continue
        selected.append(node)
    return selected


def node_name(node: dict) -> str:
    return node.get("name") or node.get("unique_id") or "?"


def node_access(node: dict) -> str:
    return node.get("access") or node.get("config", {}).get("access") or "protected"


def node_group(node: dict) -> str:
    return node.get("group") or node.get("config", {}).get("group") or ""


def node_meta(node: dict) -> dict:
    meta = {}
    config_meta = node.get("config", {}).get("meta") or {}
    if isinstance(config_meta, dict):
        meta.update(config_meta)
    own = node.get("meta") or {}
    if isinstance(own, dict):
        meta.update(own)
    return meta


def node_path(node: dict) -> str:
    path = node.get("original_file_path") or ""
    if not path and node.get("path"):
        path = "models/" + node["path"]
    return path.replace("\\", "/")


def contract_enforced(node: dict) -> bool:
    contract = node.get("contract") or node.get("config", {}).get("contract") or {}
    return bool(isinstance(contract, dict) and contract.get("enforced"))


def column_meta(column: dict) -> dict:
    meta = {}
    config_meta = (column.get("config") or {}).get("meta") or {}
    if isinstance(config_meta, dict):
        meta.update(config_meta)
    own = column.get("meta") or {}
    if isinstance(own, dict):
        meta.update(own)
    return meta


def columns_of(node: dict) -> dict[str, dict]:
    columns = node.get("columns") or {}
    if not isinstance(columns, dict):
        return {}
    normalized = {}
    for name, column in columns.items():
        if not isinstance(column, dict):
            continue
        copied = dict(column)
        copied["meta"] = column_meta(column)
        normalized[name] = copied
    return normalized


def layer_for(path: str, layers: list[dict]) -> dict | None:
    matches = [layer for layer in layers if path.startswith(layer["path_prefix"])]
    if not matches:
        return None
    return max(matches, key=lambda layer: len(layer["path_prefix"]))


def access_applies(rule: dict, access: str) -> bool:
    when = rule.get("when_access")
    if not when:
        return True
    if isinstance(when, str):
        when = [when]
    return access in when


def build_test_index(manifest: dict) -> tuple[dict, dict]:
    """Return (column test names, dependent test labels) keyed by model unique id."""
    column_tests: dict[str, dict[str, set[str]]] = {}
    dependent_labels: dict[str, set[str]] = {}
    for node in manifest.get("nodes", {}).values():
        if node.get("resource_type") != "test":
            continue
        metadata = node.get("test_metadata") or {}
        test_name = metadata.get("name")
        column = node.get("column_name") or (metadata.get("kwargs") or {}).get("column_name")
        targets = set()
        if node.get("attached_node"):
            targets.add(node["attached_node"])
        targets.update((node.get("depends_on") or {}).get("nodes") or [])
        labels = {node.get("name") or ""}
        if test_name:
            labels.add(test_name)
        for target in targets:
            if not str(target).startswith("model."):
                continue
            dependent_labels.setdefault(target, set()).update(labels)
            if column and test_name:
                column_tests.setdefault(target, {}).setdefault(column, set()).add(test_name)
    return column_tests, dependent_labels


def result(rule_id: str, node: str, status: str, details: str) -> CheckResult:
    return CheckResult(
        rule_id=rule_id,
        node=node,
        status=status,
        severity="critical",
        details=details,
    )


def not_applicable(rule: dict, name: str, access: str) -> CheckResult | None:
    if access_applies(rule, access):
        return None
    return result(rule["id"], name, "pass", f"not required for access {access}")


def check_name_prefix(rule, node, layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    if layer is None:
        return result(rule["id"], name, "fail", "model is not in a known layer, so its name cannot be checked")
    prefixes = tuple(layer["name_prefixes"])
    if name.startswith(prefixes):
        return result(rule["id"], name, "pass", f"name uses {' or '.join(prefixes)}")
    return result(
        rule["id"],
        name,
        "fail",
        f"name must start with {' or '.join(prefixes)} for the {layer['name']} layer",
    )


def check_known_layer(rule, node, layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    if layer is None:
        return result(rule["id"], name, "fail", f"path {node_path(node)} is not in a policy layer")
    return result(rule["id"], name, "pass", f"path is in the {layer['name']} layer")


def check_group(rule, node, _layer, _tests, _labels, groups) -> CheckResult:
    name = node_name(node)
    group = node_group(node)
    if group in groups:
        return result(rule["id"], name, "pass", f"group {group}")
    if not group:
        return result(rule["id"], name, "fail", "model has no group")
    return result(rule["id"], name, "fail", f"group {group} is not one of {', '.join(groups)}")


def check_access(rule, node, layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    access = node_access(node)
    if layer is None:
        return result(rule["id"], name, "fail", "access cannot be checked because the path is not in a layer")
    if access == layer["access"]:
        return result(rule["id"], name, "pass", f"access {access}")
    return result(
        rule["id"],
        name,
        "fail",
        f"access is {access}; the {layer['name']} layer requires {layer['access']}",
    )


def check_required_meta(rule, node, _layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    skipped = not_applicable(rule, name, node_access(node))
    if skipped:
        return skipped
    key = rule["key"]
    value = node_meta(node).get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        return result(rule["id"], name, "fail", f"meta.{key} is missing")
    allowed = rule.get("allowed")
    if allowed is not None and value not in allowed:
        return result(rule["id"], name, "fail", f"meta.{key} is {value!r}; allowed values are {allowed}")
    return result(rule["id"], name, "pass", f"meta.{key} is set")


def check_primary_key(rule, node, _layer, tests, _labels) -> CheckResult:
    name = node_name(node)
    skipped = not_applicable(rule, name, node_access(node))
    if skipped:
        return skipped
    key_name = rule.get("meta_key", "primary_key")
    primary_key = node_meta(node).get(key_name)
    if not isinstance(primary_key, list) or not primary_key:
        return result(rule["id"], name, "fail", f"meta.{key_name} must be a non-empty list of columns")
    columns = columns_of(node)
    missing = [column for column in primary_key if column not in columns]
    if missing:
        return result(rule["id"], name, "fail", f"meta.{key_name} names unknown columns: {missing}")
    without_not_null = [
        column
        for column in primary_key
        if "not_null" not in tests.get(node.get("unique_id"), {}).get(column, set())
    ]
    if without_not_null:
        return result(rule["id"], name, "fail", f"primary key columns need a not_null test: {without_not_null}")
    return result(rule["id"], name, "pass", "primary key columns exist and are not null")


def check_key_role(rule, node, _layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    roles = rule.get("roles") or {}
    problems = []
    present = []
    for column_name, expected in roles.items():
        column = columns_of(node).get(column_name)
        if column is None:
            continue
        present.append(column_name)
        actual = (column.get("meta") or {}).get("key_role")
        if actual != expected:
            problems.append(f"{column_name} key_role is {actual!r}; expected {expected}")
    if problems:
        return result(rule["id"], name, "fail", "; ".join(problems))
    if not present:
        return result(rule["id"], name, "pass", "no governed key columns")
    return result(rule["id"], name, "pass", "key roles match " + ", ".join(present))


def check_contract(rule, node, layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    if layer is None or not layer.get("contract"):
        layer_name = layer["name"] if layer else "unknown"
        return result(rule["id"], name, "pass", f"contract not required for the {layer_name} layer")
    if not contract_enforced(node):
        return result(rule["id"], name, "fail", "public contract is not enforced")
    untyped = [column_name for column_name, column in columns_of(node).items() if not column.get("data_type")]
    if untyped:
        return result(rule["id"], name, "fail", f"contract columns missing data_type: {untyped}")
    if not columns_of(node):
        return result(rule["id"], name, "fail", "enforced contract declares no columns")
    return result(rule["id"], name, "pass", "contract enforced and columns are typed")


def amount_columns(node: dict, pattern: re.Pattern, currency_column: str) -> list[str]:
    return [
        column_name
        for column_name in columns_of(node)
        if column_name != currency_column and pattern.search(column_name)
    ]


def check_currency_column(rule, node, _layer, tests, _labels) -> CheckResult:
    name = node_name(node)
    skipped = not_applicable(rule, name, node_access(node))
    if skipped:
        return skipped
    pattern = re.compile(rule["amount_regex"])
    currency_column = rule["currency_column"]
    amounts = amount_columns(node, pattern, currency_column)
    if not amounts:
        return result(rule["id"], name, "pass", "no monetary columns")
    column = columns_of(node).get(currency_column)
    if column is None:
        return result(rule["id"], name, "fail", f"monetary columns {amounts} require {currency_column}")
    allowed = {item.lower() for item in rule.get("currency_types") or []}
    actual = type_base(column.get("data_type"))
    if allowed and actual not in allowed:
        return result(
            rule["id"],
            name,
            "fail",
            f"{currency_column} type is {column.get('data_type')!r}; expected one of {sorted(allowed)}",
        )
    if rule.get("require_not_null"):
        tests_for_column = tests.get(node.get("unique_id"), {}).get(currency_column, set())
        if "not_null" not in tests_for_column:
            return result(rule["id"], name, "fail", f"{currency_column} needs a not_null test")
    return result(rule["id"], name, "pass", f"{currency_column} accompanies {amounts}")


def check_money_type(rule, node, _layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    skipped = not_applicable(rule, name, node_access(node))
    if skipped:
        return skipped
    pattern = re.compile(rule["amount_regex"])
    amounts = amount_columns(node, pattern, rule.get("currency_column", "currency_code"))
    if not amounts:
        return result(rule["id"], name, "pass", "no monetary columns")
    allowed = {item.lower() for item in rule["allowed_types"]}
    bad = []
    for column_name in amounts:
        data_type = columns_of(node)[column_name].get("data_type")
        if type_base(data_type) not in allowed:
            bad.append(f"{column_name} {data_type}")
    if bad:
        return result(
            rule["id"],
            name,
            "fail",
            "monetary columns must be integer minor units: " + ", ".join(bad),
        )
    return result(rule["id"], name, "pass", "monetary columns are integer minor units")


def check_temporal(rule, node, _layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    date_pattern = re.compile(rule["date_regex"])
    timestamp_pattern = re.compile(rule["timestamp_regex"])
    date_types = {item.lower() for item in rule["date_types"]}
    timestamp_types = {item.lower() for item in rule["timestamp_types"]}
    problems = []
    checked = []
    enforced = contract_enforced(node)
    for column_name, column in columns_of(node).items():
        if date_pattern.search(column_name):
            expected = date_types
            kind = "date"
        elif timestamp_pattern.search(column_name):
            expected = timestamp_types
            kind = "timestamp"
        else:
            continue
        data_type = column.get("data_type")
        if not data_type:
            if enforced:
                problems.append(f"{column_name} has no data_type")
            continue
        checked.append(column_name)
        if type_base(data_type) not in expected:
            problems.append(f"{column_name} is {data_type}, expected a {kind} type")
    if problems:
        return result(rule["id"], name, "fail", "; ".join(problems))
    if not checked:
        return result(rule["id"], name, "pass", "no declared temporal columns")
    return result(rule["id"], name, "pass", "temporal column types match their names")


def check_accepted_values(rule, node, _layer, tests, _labels) -> CheckResult:
    name = node_name(node)
    pattern = re.compile(rule["name_regex"])
    missing = []
    matched = []
    column_tests = tests.get(node.get("unique_id"), {})
    for column_name in columns_of(node):
        if not pattern.search(column_name):
            continue
        matched.append(column_name)
        if "accepted_values" not in column_tests.get(column_name, set()):
            missing.append(column_name)
    if missing:
        return result(rule["id"], name, "fail", f"status columns need accepted_values: {missing}")
    if not matched:
        return result(rule["id"], name, "pass", "no status columns")
    return result(rule["id"], name, "pass", "status columns declare accepted values")


def check_column_meta(rule, node, _layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    column = columns_of(node).get(rule["column"])
    if column is None:
        return result(rule["id"], name, "pass", f"no {rule['column']} column")
    actual = (column.get("meta") or {}).get(rule["meta_key"])
    if actual != rule["meta_value"]:
        return result(
            rule["id"],
            name,
            "fail",
            f"{rule['column']} meta.{rule['meta_key']} is {actual!r}; expected {rule['meta_value']}",
        )
    allowed = {item.lower() for item in rule.get("data_types") or []}
    actual_type = type_base(column.get("data_type"))
    if allowed and actual_type not in allowed:
        return result(
            rule["id"],
            name,
            "fail",
            f"{rule['column']} type is {column.get('data_type')!r}; expected one of {sorted(allowed)}",
        )
    return result(rule["id"], name, "pass", f"{rule['column']} matches {rule['meta_key']}")


def check_description(rule, node, _layer, _tests, _labels) -> CheckResult:
    name = node_name(node)
    description = (node.get("description") or "").strip()
    if description:
        return result(rule["id"], name, "pass", "description is set")
    return result(rule["id"], name, "fail", "description is missing")


def check_grain_test(rule, node, _layer, tests, labels) -> CheckResult:
    name = node_name(node)
    skipped = not_applicable(rule, name, node_access(node))
    if skipped:
        return skipped
    primary_key = node_meta(node).get("primary_key")
    if not isinstance(primary_key, list) or not primary_key:
        return result(rule["id"], name, "fail", "grain test cannot be checked without meta.primary_key")
    unique_id = node.get("unique_id")
    if len(primary_key) == 1:
        column_tests = tests.get(unique_id, {}).get(primary_key[0], set())
        if "unique" in column_tests:
            return result(rule["id"], name, "pass", f"unique test covers {primary_key[0]}")
        return result(rule["id"], name, "fail", f"single-column grain needs a unique test on {primary_key[0]}")
    pattern = re.compile(rule["composite_name_regex"])
    names = labels.get(unique_id, set())
    if any(pattern.search(label or "") for label in names):
        return result(rule["id"], name, "pass", "a grain test depends on the model")
    return result(
        rule["id"],
        name,
        "fail",
        f"composite grain needs a test whose name matches {rule['composite_name_regex']}",
    )


CHECKERS = {
    "name_prefix": check_name_prefix,
    "known_layer": check_known_layer,
    "access_matches_layer": check_access,
    "required_meta": check_required_meta,
    "primary_key": check_primary_key,
    "key_role": check_key_role,
    "contract": check_contract,
    "currency_column": check_currency_column,
    "money_type": check_money_type,
    "temporal_type": check_temporal,
    "accepted_values": check_accepted_values,
    "column_meta": check_column_meta,
    "description": check_description,
    "grain_test": check_grain_test,
}


def active_exception(exceptions: list[dict], rule_id: str, model: str, today: date) -> dict | None:
    matches = [
        entry
        for entry in exceptions
        if entry["rule"] == rule_id and entry["model"] == model and entry["expires_on"] >= today
    ]
    if not matches:
        return None
    return max(matches, key=lambda entry: entry["expires_on"])


def apply_exemptions(checks: list[CheckResult], exceptions: list[dict], today: date) -> list[CheckResult]:
    adjusted = []
    for check in checks:
        if check.status != "fail":
            adjusted.append(check)
            continue
        exemption = active_exception(exceptions, check.rule_id, check.node, today)
        if exemption is None:
            adjusted.append(check)
            continue
        adjusted.append(
            result(
                check.rule_id,
                check.node,
                "exempt",
                f"exempt until {exemption['expires_on'].isoformat()}: {exemption['reason']}",
            )
        )
    return adjusted


def exception_checks(exceptions: list[dict], present_models: set[str], today: date) -> list[CheckResult]:
    checks = []
    for entry in exceptions:
        node = entry["model"]
        if entry["require_present"] and node not in present_models:
            checks.append(
                result("EXC-01", node, "fail", f"exception for {entry['rule']} targets a model that is not in the manifest")
            )
        if entry["expires_on"] < today:
            checks.append(
                result(
                    "EXC-01",
                    node,
                    "fail",
                    f"exception for {entry['rule']} expired on {entry['expires_on'].isoformat()}",
                )
            )
    return checks


def evaluate(manifest: dict, policy: dict, exceptions: list[dict], today: date | None = None) -> list[CheckResult]:
    today = today or date.today()
    validate_policy(policy)
    column_tests, dependent_labels = build_test_index(manifest)
    layers = policy["layers"]
    groups = policy["groups"]
    nodes = model_nodes(manifest)
    checks: list[CheckResult] = []
    if not nodes:
        checks.append(result("GATE-01", "", "fail", "manifest contains no project models"))
    for node in nodes:
        layer = layer_for(node_path(node), layers)
        for rule in policy["rules"]:
            kind = rule["kind"]
            if kind == "group_allowed":
                outcome = check_group(rule, node, layer, column_tests, dependent_labels, groups)
            else:
                outcome = CHECKERS[kind](rule, node, layer, column_tests, dependent_labels)
            checks.append(outcome)
    checks = apply_exemptions(checks, exceptions, today)
    present = {node_name(node) for node in nodes}
    checks.extend(exception_checks(exceptions, present, today))
    checks.sort(key=lambda item: (item.rule_id, item.node, item.details))
    return checks


def summarize(checks: list[CheckResult]) -> dict:
    failed = [check for check in checks if check.status == "fail"]
    payload_checks = []
    for check in checks:
        body = asdict(check)
        body["name"] = check.name
        if check.status == "exempt":
            body["exempt"] = True
        payload_checks.append(body)
    return {
        "status": "fail" if failed else "pass",
        "score": len(checks) - len(failed),
        "max_score": len(checks),
        "rule_ids": sorted({check.rule_id for check in checks}),
        "checks": payload_checks,
    }


def markdown_summary(summary: dict) -> str:
    counts: dict[str, dict[str, int]] = {}
    failures = []
    for check in summary["checks"]:
        bucket = counts.setdefault(check["rule_id"], {"pass": 0, "exempt": 0, "fail": 0})
        bucket[check["status"]] = bucket.get(check["status"], 0) + 1
        if check["status"] == "fail":
            failures.append(check)
    lines = [
        f"### Governance quality gate: {summary['status']}",
        "",
        f"Score: {summary['score']}/{summary['max_score']}",
        "",
        "| Rule | Pass | Exempt | Fail |",
        "| --- | ---: | ---: | ---: |",
    ]
    for rule_id in sorted(counts):
        bucket = counts[rule_id]
        lines.append(
            f"| {rule_id} | {bucket.get('pass', 0)} | {bucket.get('exempt', 0)} | {bucket.get('fail', 0)} |"
        )
    if failures:
        lines.extend(["", "| Rule | Node | Detail |", "| --- | --- | --- |"])
        for check in failures:
            detail = check["details"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {check['rule_id']} | {check['node']} | {detail} |")
    lines.append("")
    return "\n".join(lines)


def print_human(summary: dict, verbose: bool = False) -> None:
    status = "PASSED" if summary["status"] == "pass" else "FAILED"
    print(f"Governance quality gate: {status}")
    print()
    for check in summary["checks"]:
        if not verbose and check["status"] == "pass":
            continue
        marker = "[x]" if check["status"] in {"pass", "exempt"} else "[ ]"
        print(f"{marker} {check['name']}: {check['details']}")
    if any(check["status"] != "pass" for check in summary["checks"]):
        print()
    counts: dict[str, dict[str, int]] = {}
    for check in summary["checks"]:
        bucket = counts.setdefault(check["rule_id"], {"pass": 0, "exempt": 0, "fail": 0})
        bucket[check["status"]] = bucket.get(check["status"], 0) + 1
    print(f"{'Rule':<8} {'Pass':>6} {'Exempt':>7} {'Fail':>6}")
    for rule_id in sorted(counts):
        bucket = counts[rule_id]
        print(
            f"{rule_id:<8} {bucket.get('pass', 0):>6} {bucket.get('exempt', 0):>7} {bucket.get('fail', 0):>6}"
        )
    print()
    print(f"Score: {summary['score']}/{summary['max_score']}")
    print("Rules: " + ", ".join(summary["rule_ids"]))


def write_markdown(summary: dict, path: Path | None) -> None:
    targets = []
    if path is not None:
        targets.append(path)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        targets.append(Path(step_summary))
    text = markdown_summary(summary)
    for target in targets:
        with target.open("a", encoding="utf-8") as handle:
            handle.write(text)


def run_from_files(
    manifest_path: Path,
    policy_path: Path,
    exceptions_path: Path,
    today: date | None = None,
) -> dict:
    if not manifest_path.exists():
        raise SystemExit(
            f"Manifest not found at {manifest_path}. Run dbt parse or make build before the governance gate."
        )
    policy = load_yaml(policy_path)
    exceptions = validate_exceptions(load_yaml(exceptions_path), policy)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return summarize(evaluate(manifest, policy, exceptions, today))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate project models against governance/policy.yml.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--verbose", action="store_true", help="Print every check, including passes.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--exceptions", type=Path, default=DEFAULT_EXCEPTIONS)
    parser.add_argument("--markdown", type=Path, help="Append a markdown summary to this file.")
    parser.add_argument("--today", type=as_date, help="Override the date used for exception expiry (YYYY-MM-DD).")
    args = parser.parse_args(argv)

    summary = run_from_files(args.manifest, args.policy, args.exceptions, args.today)
    write_markdown(summary, args.markdown)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_human(summary, verbose=args.verbose)
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

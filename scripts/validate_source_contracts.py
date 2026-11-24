"""Validate raw lending files against contracts/sources/*.yml.

Runs before dbt. A failure names the data file, the line (header is line 1),
and the field. The contract document itself is checked too: a missing
idempotency key, a missing evolution class, or an unknown rule kind fails here
rather than being silently ignored.

    python scripts/validate_source_contracts.py
    python scripts/validate_source_contracts.py contracts/sources/loan_events.yml
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "contracts" / "sources"
CONTRACT_VERSION = 1
EVOLUTION_CLASSES = {"additive", "breaking", "restatement"}
FIELD_KEYS = {"name", "type", "nullable", "enum", "unit", "description"}
TYPES = {"string", "integer", "date", "timestamp"}
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INTEGER = re.compile(r"^-?\d+$")
DATASET_RULES = {"unique", "timestamp_order", "present_iff", "const_when", "sum_equals", "supersede_matches"}
CROSS_RULES = {"references", "matches_parent"}
REQUIRED_TIME = ("effective_at", "recorded_at", "_loaded_at")


@dataclass
class Violation:
    file: str
    line: int | None
    field: str | None
    message: str

    def format(self) -> str:
        location = self.file if self.line is None else f"{self.file}:{self.line}"
        if self.field:
            return f"{location}: {self.field}: {self.message}"
        return f"{location}: {self.message}"


def resolve(file_value: str) -> Path:
    path = Path(file_value)
    if path.is_absolute():
        return path
    return ROOT / path


def display_path(file_value: str) -> str:
    path = Path(file_value)
    if path.is_absolute():
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)
    return file_value


def when_matches(row: dict, clauses: list[dict] | None) -> bool:
    if not clauses:
        return True
    for clause in clauses:
        value = row[clause["field"]]
        if "equals" in clause and value != clause["equals"]:
            return False
        if "in" in clause and value not in clause["in"]:
            return False
    return True


def check_document(document: dict, contract_path: Path) -> list[Violation]:
    own = display_path(str(contract_path.relative_to(ROOT)) if contract_path.is_relative_to(ROOT) else contract_path)
    errors: list[Violation] = []

    def fail(section: str, message: str) -> None:
        errors.append(Violation(own, None, section, message))

    if not isinstance(document, dict):
        fail(None, "contract must be a YAML mapping")
        return errors
    if document.get("version") != CONTRACT_VERSION:
        fail("version", f"must be {CONTRACT_VERSION}")
    for section in ("producer", "consumer", "delivery", "notification", "time", "units", "datasets", "evolution"):
        if section not in document:
            fail(section, "is missing")
    delivery = document.get("delivery") or {}
    if delivery.get("mode") != "daily_batch":
        fail("delivery.mode", "must be daily_batch")
    if delivery.get("idempotency_key") != "event_id":
        fail("delivery.idempotency_key", "must be event_id")
    time = document.get("time") or {}
    for name in REQUIRED_TIME:
        if name not in time:
            fail("time", f"missing {name}")
    notification = document.get("notification") or {}
    for key in ("channel", "additive_notice", "breaking_notice", "restatement"):
        if not notification.get(key):
            fail(f"notification.{key}", "is missing")
    evolution = document.get("evolution") or []
    if not evolution:
        fail("evolution", "needs the additive-vs-breaking table")
    classes = set()
    for index, row in enumerate(evolution):
        kind = row.get("class") if isinstance(row, dict) else None
        if kind not in EVOLUTION_CLASSES:
            fail(f"evolution[{index}].class", f"{kind!r} is not one of {sorted(EVOLUTION_CLASSES)}")
        elif not row.get("change"):
            fail(f"evolution[{index}].change", "is missing")
        else:
            classes.add(kind)
    if evolution and classes != EVOLUTION_CLASSES:
        fail("evolution", f"must include each of {sorted(EVOLUTION_CLASSES)}")
    source = document.get("dbt_source")
    if source and not resolve(source).is_file():
        fail("dbt_source", f"{source} does not exist")
    datasets = document.get("datasets") or []
    names = [dataset.get("name") for dataset in datasets]
    if len(names) != len(set(names)):
        fail("datasets", "duplicate dataset name")
    for dataset in datasets:
        errors.extend(check_dataset_shape(dataset, own))
    for rule in document.get("checks") or []:
        if rule.get("kind") not in CROSS_RULES:
            fail("checks", f"unknown kind {rule.get('kind')!r}")
    return errors


def check_dataset_shape(dataset: dict, contract_file: str) -> list[Violation]:
    errors: list[Violation] = []
    label = dataset.get("name") or "?"

    def fail(field: str | None, message: str) -> None:
        errors.append(Violation(contract_file, None, f"{label}.{field}" if field else label, message))

    for key in ("name", "file", "fields", "rules"):
        if key not in dataset:
            fail(key, "is missing")
    fields = dataset.get("fields") or []
    seen = set()
    for field in fields:
        unknown = set(field) - FIELD_KEYS
        if unknown:
            fail(field.get("name"), f"unknown keys {sorted(unknown)}")
        name = field.get("name")
        if name in seen:
            fail(name, "duplicate field")
        seen.add(name)
        if field.get("type") not in TYPES:
            fail(name, f"unknown type {field.get('type')!r}")
        if "nullable" not in field:
            fail(name, "nullable is missing")
        if str(name).endswith("_minor") and field.get("unit") != "minor":
            fail(name, "minor-unit amounts must set unit: minor")
        if field.get("unit") == "minor" and field.get("type") != "integer":
            fail(name, "unit minor must be an integer")
    for required in ("event_id", *REQUIRED_TIME):
        match = next((field for field in fields if field.get("name") == required), None)
        if match is None:
            fail(required, "is required on every dataset")
        elif required == "event_id" and (match.get("type") != "string" or match.get("nullable") is not False):
            fail("event_id", "must be a required string")
        elif required in REQUIRED_TIME and match.get("type") != "timestamp":
            fail(required, "must be a timestamp")
    event_type = next((field for field in fields if field.get("name") == "event_type"), None)
    if event_type is None or not event_type.get("enum"):
        fail("event_type", "must declare an enum")
    rules = dataset.get("rules") or []
    if not any(rule.get("kind") == "unique" and rule.get("fields") == ["event_id"] for rule in rules):
        fail("rules", "needs unique on event_id")
    if not any(rule.get("kind") == "timestamp_order" for rule in rules):
        fail("rules", "needs timestamp_order")
    for rule in rules:
        if rule.get("kind") not in DATASET_RULES:
            fail("rules", f"unknown kind {rule.get('kind')!r}")
    return errors


def parse_field(field: dict, raw: str | None) -> tuple[object, str | None]:
    if raw is None or raw == "":
        if field["nullable"]:
            return None, None
        return None, "is null"
    kind = field["type"]
    if kind == "string":
        allowed = field.get("enum")
        if allowed is not None and raw not in allowed:
            return None, f"value {raw!r} is not allowed ({', '.join(allowed)})"
        return raw, None
    if kind == "integer":
        if not INTEGER.fullmatch(raw):
            return None, f"value {raw!r} is not an integer"
        value = int(raw)
        if field.get("unit") == "minor" and value < 0:
            return None, f"value {value} is a negative minor unit"
        return value, None
    if kind == "date":
        if not DATE.fullmatch(raw):
            return None, f"value {raw!r} is not an ISO date"
        try:
            datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return None, f"value {raw!r} is not a real date"
        return raw, None
    if not TIMESTAMP.fullmatch(raw):
        return None, f"value {raw!r} is not a UTC timestamp YYYY-MM-DDTHH:MM:SSZ"
    try:
        datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None, f"value {raw!r} is not a real timestamp"
    return raw, None


def load_dataset(dataset: dict) -> tuple[str, list[tuple[int, dict]], list[Violation]]:
    file_value = dataset["file"]
    shown = display_path(file_value)
    path = resolve(file_value)
    errors: list[Violation] = []
    if not path.is_file():
        errors.append(Violation(shown, None, None, "file is missing"))
        return shown, [], errors
    expected = [field["name"] for field in dataset["fields"]]
    by_name = {field["name"]: field for field in dataset["fields"]}
    parsed: list[tuple[int, dict]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            errors.append(Violation(shown, 1, None, "file is empty"))
            return shown, [], errors
        if header != expected:
            errors.append(Violation(shown, 1, None, f"header {header} != contract fields {expected}"))
            return shown, [], errors
        for line_number, raw_row in enumerate(reader, start=2):
            if len(raw_row) != len(expected):
                errors.append(Violation(shown, line_number, None, f"expected {len(expected)} columns, found {len(raw_row)}"))
                continue
            typed: dict = {}
            bad = False
            for name, raw in zip(expected, raw_row):
                value, message = parse_field(by_name[name], raw)
                if message:
                    errors.append(Violation(shown, line_number, name, message))
                    bad = True
                else:
                    typed[name] = value
            if not bad:
                parsed.append((line_number, typed))
    return shown, parsed, errors


def apply_dataset_rules(dataset: dict, shown: str, rows: list[tuple[int, dict]]) -> list[Violation]:
    errors: list[Violation] = []
    for rule in dataset.get("rules") or []:
        kind = rule["kind"]
        if kind == "unique":
            errors.extend(rule_unique(shown, rows, rule))
        elif kind == "timestamp_order":
            errors.extend(rule_timestamp_order(shown, rows, rule))
        elif kind == "present_iff":
            errors.extend(rule_present_iff(shown, rows, rule))
        elif kind == "const_when":
            errors.extend(rule_const_when(shown, rows, rule))
        elif kind == "sum_equals":
            errors.extend(rule_sum_equals(shown, rows, rule))
        elif kind == "supersede_matches":
            errors.extend(rule_supersede(shown, rows, rule))
    return errors


def rule_unique(shown: str, rows: list[tuple[int, dict]], rule: dict) -> list[Violation]:
    fields = rule["fields"]
    seen: dict[tuple, int] = {}
    errors = []
    for line, row in rows:
        if not when_matches(row, rule.get("when")):
            continue
        key = tuple(row[name] for name in fields)
        if key in seen:
            errors.append(
                Violation(
                    shown,
                    line,
                    fields[0] if len(fields) == 1 else ",".join(fields),
                    f"duplicate {key if len(fields) > 1 else key[0]!r} (first line {seen[key]})",
                )
            )
        else:
            seen[key] = line
    return errors


def rule_timestamp_order(shown: str, rows: list[tuple[int, dict]], rule: dict) -> list[Violation]:
    fields = rule["fields"]
    errors = []
    for line, row in rows:
        values = [row[name] for name in fields]
        if values != sorted(values):
            errors.append(Violation(shown, line, fields[0], f"{' <= '.join(fields)} is violated ({values})"))
    return errors


def rule_present_iff(shown: str, rows: list[tuple[int, dict]], rule: dict) -> list[Violation]:
    errors = []
    field = rule["field"]
    for line, row in rows:
        present = row[field] is not None
        required = when_matches(row, rule["when"])
        if present != required:
            state = "is set" if present else "is null"
            errors.append(Violation(shown, line, field, f"{state} but the contract says otherwise"))
    return errors


def rule_const_when(shown: str, rows: list[tuple[int, dict]], rule: dict) -> list[Violation]:
    errors = []
    for line, row in rows:
        if when_matches(row, rule.get("when")) and row[rule["field"]] != rule["value"]:
            errors.append(
                Violation(shown, line, rule["field"], f"value {row[rule['field']]!r} != {rule['value']!r}")
            )
    return errors


def rule_sum_equals(shown: str, rows: list[tuple[int, dict]], rule: dict) -> list[Violation]:
    errors = []
    for line, row in rows:
        if not when_matches(row, rule.get("when")):
            continue
        total = sum(row[name] for name in rule["parts"])
        if total != row[rule["total"]]:
            errors.append(
                Violation(
                    shown,
                    line,
                    rule["total"],
                    f"{' + '.join(rule['parts'])} = {total} != {row[rule['total']]}",
                )
            )
    return errors


def rule_supersede(shown: str, rows: list[tuple[int, dict]], rule: dict) -> list[Violation]:
    scheduled = {
        row["instalment_id"]: (line, row)
        for line, row in rows
        if row["event_type"] == "instalment_scheduled"
    }
    errors = []
    for line, row in rows:
        if row["event_type"] != "instalment_superseded":
            continue
        prior = scheduled.get(row["instalment_id"])
        if prior is None:
            errors.append(Violation(shown, line, "instalment_id", f"{row['instalment_id']!r} has no instalment_scheduled"))
            continue
        prior_line, prior_row = prior
        for field in rule["fields"]:
            if row[field] != prior_row[field]:
                errors.append(
                    Violation(
                        shown,
                        line,
                        field,
                        f"value {row[field]!r} != scheduled value {prior_row[field]!r} (line {prior_line})",
                    )
                )
        if row["effective_at"] < prior_row["effective_at"]:
            errors.append(Violation(shown, line, "effective_at", "supersede is earlier than the scheduled row"))
    return errors


def index_parent(rows: list[tuple[int, dict]], fields: list[str], clauses: list[dict] | None) -> dict[tuple, tuple[int, dict]]:
    found: dict[tuple, tuple[int, dict]] = {}
    for line, row in rows:
        if when_matches(row, clauses):
            found[tuple(row[name] for name in fields)] = (line, row)
    return found


def apply_cross_rules(document: dict, books: dict[str, tuple[str, list[tuple[int, dict]]]]) -> list[Violation]:
    errors: list[Violation] = []
    for rule in document.get("checks") or []:
        kind = rule["kind"]
        child_shown, child_rows = books[rule["child"]]
        parent_shown, parent_rows = books[rule["parent"]]
        if kind == "references":
            parent = index_parent(parent_rows, rule["parent_fields"], rule.get("parent_when"))
            for line, row in child_rows:
                if not when_matches(row, rule.get("child_when")):
                    continue
                key = tuple(row[name] for name in rule["child_fields"])
                if key not in parent:
                    errors.append(
                        Violation(
                            child_shown,
                            line,
                            rule["child_fields"][0],
                            f"{key[0]!r} is not in {rule['parent']}.{rule['parent_fields'][0]}",
                        )
                    )
        elif kind == "matches_parent":
            parent = index_parent(parent_rows, rule["key"], rule.get("parent_when"))
            for line, row in child_rows:
                key = tuple(row[name] for name in rule["key"])
                prior = parent.get(key)
                if prior is None:
                    continue
                for field in rule["fields"]:
                    if row[field] != prior[1][field]:
                        errors.append(
                            Violation(
                                child_shown,
                                line,
                                field,
                                f"value {row[field]!r} != {rule['parent']} {prior[1][field]!r} (line {prior[0]} in {parent_shown})",
                            )
                        )
    return errors


def validate_document(document: dict, contract_path: Path) -> list[Violation]:
    errors = check_document(document, contract_path)
    # Shape errors still try to read files so a bad row is reported in the same run
    # when the datasets are well formed enough to load.
    if not isinstance(document, dict) or not document.get("datasets"):
        return errors
    books: dict[str, tuple[str, list[tuple[int, dict]]]] = {}
    for dataset in document["datasets"]:
        if not dataset.get("file") or not dataset.get("fields"):
            continue
        shown, rows, load_errors = load_dataset(dataset)
        errors.extend(load_errors)
        errors.extend(apply_dataset_rules(dataset, shown, rows))
        books[dataset["name"]] = (shown, rows)
    if all(dataset.get("name") in books for dataset in document["datasets"]):
        errors.extend(apply_cross_rules(document, books))
    return errors


def validate_path(path: Path) -> list[Violation]:
    if not path.is_file():
        return [Violation(str(path), None, None, "contract file is missing")]
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return validate_document(loaded or {}, path)


def contract_paths(arguments: list[str]) -> list[Path]:
    if arguments:
        return [Path(value) if Path(value).is_absolute() else ROOT / value for value in arguments]
    return sorted(DEFAULT_DIR.glob("*.yml"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate raw files against source contracts.")
    parser.add_argument("contracts", nargs="*", help="Contract YAML files. Default: contracts/sources/*.yml.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    paths = contract_paths(args.contracts)
    if not paths:
        print(f"no source contracts in {DEFAULT_DIR}", file=sys.stderr)
        return 1
    failures = []
    for path in paths:
        failures.extend(validate_path(path))
    if failures:
        for failure in failures:
            print(failure.format(), file=sys.stderr)
        print(f"source contracts: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print(f"source contracts: {len(paths)} file(s), ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

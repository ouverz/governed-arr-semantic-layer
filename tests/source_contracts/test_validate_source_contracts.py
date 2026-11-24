import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_lending_data as gen
import validate_source_contracts as contracts


CONTRACT = ROOT / "contracts" / "sources" / "loan_events.yml"
SOURCE = ROOT / "models" / "staging" / "lending" / "_lending__sources.yml"
SEEDS = ROOT / "seeds" / "lending" / "_lending__seeds.yml"
TYPE_MAP = {"string": "varchar", "integer": "bigint", "date": "date", "timestamp": "timestamp"}


def test_golden_files_pass_the_loan_events_contract():
    assert contracts.validate_path(CONTRACT) == []


def test_unknown_event_type_names_file_line_and_field(tmp_path):
    original = (ROOT / "seeds" / "lending" / "raw_lending__repayments.csv").read_text(encoding="utf-8").splitlines()
    cells = original[1].split(",")
    cells[1] = "not_a_real_event"
    original[1] = ",".join(cells)
    bad = tmp_path / "raw_lending__repayments.csv"
    bad.write_text("\n".join(original) + "\n", encoding="utf-8")
    text = CONTRACT.read_text(encoding="utf-8").replace(
        "seeds/lending/raw_lending__repayments.csv",
        bad.as_posix(),
    )
    path = tmp_path / "loan_events.yml"
    path.write_text(text, encoding="utf-8")

    failures = contracts.validate_path(path)
    assert failures
    rendered = [item.format() for item in failures]
    match = next(item for item in rendered if "event_type" in item and "not_a_real_event" in item)
    assert bad.as_posix() in match
    assert ":2:" in match
    assert "event_type" in match


def test_duplicate_idempotency_key_names_the_field(tmp_path):
    document = {
        "version": 1,
        "producer": {"owner": "lending-backend@arr-lab.example"},
        "consumer": {"owner": "data@arr-lab.example"},
        "delivery": {"mode": "daily_batch", "idempotency_key": "event_id"},
        "notification": {
            "channel": "lending-backend@arr-lab.example",
            "additive_notice": "1 business day",
            "breaking_notice": "60 days",
            "restatement": "tell the consumer first",
        },
        "time": {"effective_at": "business", "recorded_at": "commit", "_loaded_at": "batch"},
        "units": {},
        "evolution": [
            {"change": "add nullable column", "class": "additive"},
            {"change": "rename", "class": "breaking"},
            {"change": "fix a payload", "class": "restatement"},
        ],
        "datasets": [
            {
                "name": "repayments",
                "file": "events.csv",
                "fields": [
                    {"name": "event_id", "type": "string", "nullable": False},
                    {
                        "name": "event_type",
                        "type": "string",
                        "nullable": False,
                        "enum": ["repayment_posted", "draw_posted"],
                    },
                    {"name": "effective_at", "type": "timestamp", "nullable": False},
                    {"name": "recorded_at", "type": "timestamp", "nullable": False},
                    {"name": "_loaded_at", "type": "timestamp", "nullable": False},
                ],
                "rules": [
                    {"kind": "unique", "fields": ["event_id"]},
                    {"kind": "timestamp_order", "fields": ["effective_at", "recorded_at", "_loaded_at"]},
                ],
            }
        ],
    }
    rows = [
        "event_id,event_type,effective_at,recorded_at,_loaded_at",
        "evt_pmt_000001,repayment_posted,2025-03-20T10:00:00Z,2025-03-20T10:00:00Z,2025-03-21T06:00:00Z",
        "evt_pmt_000001,draw_posted,2025-03-21T10:00:00Z,2025-03-21T10:00:00Z,2025-03-22T06:00:00Z",
    ]
    (tmp_path / "events.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    document["datasets"][0]["file"] = str(tmp_path / "events.csv")
    path = tmp_path / "mini.yml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    rendered = [item.format() for item in contracts.validate_path(path)]
    assert any(":3:" in item and "event_id" in item and "duplicate" in item for item in rendered)


def test_generator_columns_match_the_contract():
    document = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    for dataset in document["datasets"]:
        expected = [(field["name"], field["type"]) for field in dataset["fields"]]
        assert gen.COLUMNS[dataset["name"]] == expected


def test_dbt_source_columns_match_the_contract():
    document = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["sources"][0]
    tables = {table["name"]: table for table in source["tables"]}
    assert source["config"]["loaded_at_field"] == "_loaded_at"
    assert source["config"]["freshness"]["warn_after"]["count"] == 24
    assert source["config"]["freshness"]["error_after"]["count"] == 36
    assert source["config"]["meta"]["owner"] == "Lending backend"
    assert source["config"]["meta"]["contract"] == "contracts/sources/loan_events.yml"
    for dataset in document["datasets"]:
        columns = tables[f"raw_lending__{dataset['name']}"]["columns"]
        assert [column["name"] for column in columns] == [field["name"] for field in dataset["fields"]]
        for column, field in zip(columns, dataset["fields"]):
            assert column["data_type"] == TYPE_MAP[field["type"]]


def test_seed_accepted_values_match_contract_enums():
    document = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    enums = {}
    for dataset in document["datasets"]:
        enums[f"raw_lending__{dataset['name']}"] = {
            field["name"]: field["enum"] for field in dataset["fields"] if field.get("enum")
        }
    seeds = yaml.safe_load(SEEDS.read_text(encoding="utf-8"))["seeds"]
    for seed in seeds:
        for column in seed["columns"]:
            for test in column.get("data_tests") or []:
                if not isinstance(test, dict) or "accepted_values" not in test:
                    continue
                assert test["accepted_values"]["arguments"]["values"] == enums[seed["name"]][column["name"]]

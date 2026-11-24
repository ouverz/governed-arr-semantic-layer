"""Tiny manifest builders for governance gate tests.

These are not dbt models. They are the smallest manifest shape the gate reads.
"""

from __future__ import annotations

PROJECT = "arr_semantic_layer_lab"


def _model_id(name: str) -> str:
    return f"model.{PROJECT}.{name}"


def column(name: str, data_type: str, key_role: str | None = None, description: str = "") -> dict:
    body = {"name": name, "data_type": data_type, "description": description or name}
    if key_role:
        body["meta"] = {"key_role": key_role}
    return body


def not_null_test(model_name: str, column_name: str) -> dict:
    model_id = _model_id(model_name)
    return {
        "resource_type": "test",
        "package_name": PROJECT,
        "name": f"not_null_{model_name}_{column_name}",
        "attached_node": model_id,
        "column_name": column_name,
        "test_metadata": {"name": "not_null", "kwargs": {"column_name": column_name}},
        "depends_on": {"nodes": [model_id]},
    }


def unique_test(model_name: str, column_name: str) -> dict:
    model_id = _model_id(model_name)
    return {
        "resource_type": "test",
        "package_name": PROJECT,
        "name": f"unique_{model_name}_{column_name}",
        "attached_node": model_id,
        "column_name": column_name,
        "test_metadata": {"name": "unique", "kwargs": {"column_name": column_name}},
        "depends_on": {"nodes": [model_id]},
    }


def accepted_values_test(model_name: str, column_name: str) -> dict:
    model_id = _model_id(model_name)
    return {
        "resource_type": "test",
        "package_name": PROJECT,
        "name": f"accepted_values_{model_name}_{column_name}",
        "attached_node": model_id,
        "column_name": column_name,
        "test_metadata": {"name": "accepted_values", "kwargs": {"column_name": column_name}},
        "depends_on": {"nodes": [model_id]},
    }


def grain_test(model_name: str) -> dict:
    model_id = _model_id(model_name)
    return {
        "resource_type": "test",
        "package_name": PROJECT,
        "name": f"assert_{model_name}_grain",
        "depends_on": {"nodes": [model_id]},
    }


def public_meta(**overrides) -> dict:
    meta = {
        "owner": "Data",
        "business_owner": "RevOps",
        "tier": "certified",
        "grain": "loan_id x month_end_date",
        "freshness_sla": "lab: calendar month-end fixture, rebuilt on demand",
        "primary_key": ["loan_id", "month_end_date"],
    }
    meta.update(overrides)
    return meta


def lending_fact(**overrides) -> dict:
    """A public mart that satisfies the policy with metadata only."""
    name = overrides.pop("name", "fct_loan_month_end")
    columns = {
        "loan_id": column("loan_id", "varchar"),
        "month_end_date": column("month_end_date", "date"),
        "customer_id": column("customer_id", "varchar", key_role="conformed_customer"),
        "outstanding_principal_minor": column("outstanding_principal_minor", "bigint"),
        "currency_code": column("currency_code", "varchar"),
        "loan_status": column("loan_status", "varchar"),
        "country_code": column(
            "country_code",
            "varchar",
            description="ISO 3166-1 alpha-2 country",
        ),
        "recorded_at": column("recorded_at", "timestamp"),
    }
    columns["country_code"]["meta"] = {"geo_standard": "iso_3166_1_alpha_2"}
    node = {
        "resource_type": "model",
        "package_name": PROJECT,
        "unique_id": _model_id(name),
        "name": name,
        "original_file_path": f"models/marts/lending/{name}.sql",
        "description": "Loan month-end balances for the lending lab.",
        "access": "public",
        "group": "lending",
        "contract": {"enforced": True},
        "meta": public_meta(),
        "columns": columns,
    }
    node.update(overrides)
    return node


def tests_for_lending(model_name: str = "fct_loan_month_end") -> list[dict]:
    columns = [
        "loan_id",
        "month_end_date",
        "customer_id",
        "outstanding_principal_minor",
        "currency_code",
        "loan_status",
        "country_code",
        "recorded_at",
    ]
    nodes = [not_null_test(model_name, column_name) for column_name in columns]
    nodes.append(accepted_values_test(model_name, "loan_status"))
    nodes.append(grain_test(model_name))
    return nodes


def manifest_from(models: list[dict], tests: list[dict] | None = None) -> dict:
    nodes = {}
    for model in models:
        nodes[model["unique_id"]] = model
    for index, test in enumerate(tests or []):
        nodes[f"test.{PROJECT}.fixture_{index}"] = test
    return {"metadata": {"project_name": PROJECT}, "nodes": nodes}


def missing_owner_manifest() -> dict:
    model = lending_fact(name="fct_arr_snapshot")
    model["original_file_path"] = "models/marts/revenue/fct_arr_snapshot.sql"
    model["group"] = "revenue"
    model["meta"] = public_meta(owner=None, grain="snapshot_date x account_id", primary_key=["snapshot_date", "account_id"])
    model["meta"].pop("owner")
    model["columns"] = {
        "snapshot_date": column("snapshot_date", "date"),
        "account_id": column("account_id", "varchar", key_role="salesforce_account"),
        "ending_arr": column("ending_arr", "bigint"),
        "currency_code": column("currency_code", "varchar"),
    }
    tests = [
        not_null_test("fct_arr_snapshot", "snapshot_date"),
        not_null_test("fct_arr_snapshot", "account_id"),
        not_null_test("fct_arr_snapshot", "ending_arr"),
        not_null_test("fct_arr_snapshot", "currency_code"),
        grain_test("fct_arr_snapshot"),
    ]
    return manifest_from([model], tests)

# ARR Semantic Layer Lab

A minimal, production-shaped ARR metric product with governed definitions,
repeatable validation, and a clear operating model from raw inputs to
consumable metrics.

This repository demonstrates one certified business metric, Ending ARR,
implemented as a governed data product rather than a loose analytics demo.
The local MVP uses DuckDB for reproducible validation and includes the
Snowflake deployment path as part of the operating model, not as an afterthought.

## What this project proves

- one metric can be defined explicitly and certified end to end;
- business rules can be owned, versioned, tested, and reviewed;
- public marts can be protected with contracts;
- semantic consumption can sit on top of governed definitions; and
- CI/CD can validate the pipeline before deployment.

For a reviewer-friendly walkthrough, start with
[`docs/evaluation_guide.md`](docs/evaluation_guide.md).

## What this project does not claim

- it is not a full finance system;
- it is not a live production ingestion pipeline in the local lab;
- it does not prove a hosted dbt Semantic Layer query path locally;
- it is intentionally scoped to one certified metric, not a broad analytics platform; and
- the lending files are a synthetic source contract, not a certified balance, a days-past-due figure, or a credit decision.

## Portfolio Highlights

- One governed metric, Ending ARR, defined end to end.
- Real ARR edge cases: billing intervals, discounts, exclusions, churn, reactivation, and renewals.
- A documented metric contract, singular business tests, and model/unit tests that prove the logic.
- Data-quality observability models around the ARR staging inputs.
- A governance quality gate that checks every model against `governance/policy.yml`, not a list of file names.
- A documented metric-change example for excluding paused subscriptions prospectively.
- A governed consumption story that distinguishes certified BI and AI reuse from raw-table interpretation.
- A reproducible local build that reviewers can run with Docker only.

## Operating-model controls

The project includes a data-quality observability layer for completeness, validity, duplicates, freshness/coverage, and referential integrity across ARR staging inputs. It also includes a governance quality gate that reads the dbt manifest and checks naming, ownership, access, contracts, grain, and money rules. The conventions are in [`docs/architecture/conventions.md`](docs/architecture/conventions.md).

See [`docs/data_quality.md`](docs/data_quality.md), [`docs/governance_quality_gate.md`](docs/governance_quality_gate.md), and [`docs/change_examples/exclude_paused_subscriptions.md`](docs/change_examples/exclude_paused_subscriptions.md).

The repo is structured like a hands-on lab, but the implementation goal is a
production-style operating model: explicit metric ownership, reviewed definition
changes, repeatable local validation, Snowflake deployment, and post-deploy
semantic checks.

## Semantic consumption paths

The project includes two complementary semantic layers over the same governed
marts:

- [`models/semantic/sem_arr.yml`](models/semantic/sem_arr.yml) defines the
  dbt Semantic Layer surface for MetricFlow-compatible consumers.
- [`models/snowflake_semantic/revenue_metrics.sql`](models/snowflake_semantic/revenue_metrics.sql)
  defines the Snowflake native semantic view for Snowflake-native consumption,
  including future Cortex Analyst or Cortex Agent use cases.

Both paths depend on `fct_arr_snapshot`, `fct_arr_movement`, and `dim_account`.
That keeps the certified ARR definition in the marts and lets different
consumption tools reuse the same governed logic instead of redefining ARR
downstream.

## Selected visuals

These two views show the shape of the system without making the README a wall of text.

![ARR lineage and transformation layers](<images/Screenshot 2026-06-22 at 23.26.22.png>)

![ARR fact and test nodes](<images/Screenshot 2026-06-22 at 23.27.46.png>)

## Pattern borrowed from mature revenue stacks

The project follows a pattern used by stronger revenue analytics teams: keep raw inputs separate, derive historical truth with effective dates, and expose a clean consumption layer on top. In practice that means the ARR logic is anchored in point-in-time snapshot facts rather than current-state rows, so month-end truth stays stable and explainable. The same separation also makes it easier to publish a certified dataset for BI or semantic consumption without asking downstream users to interpret raw source tables directly.

## SME lending

The same fictional customers also have a synthetic SME lending batch in
[`seeds/lending/`](seeds/lending/). Eight named loans reuse the Salesforce
`account_id` values, including one revolving credit line. Money is integer
minor units plus `currency_code`. Every event has `effective_at`,
`recorded_at`, and `_loaded_at`.

This is the producer contract ([`contracts/sources/loan_events.yml`](contracts/sources/loan_events.yml))
and the dbt source declaration. Staging keeps both timestamps. The loan
ledger is the only balance calculation, and `fct_loan_month_end` (v1) publishes
outstanding principal and days past due as known 5 days after month-end.
`dim_customer` maps each Salesforce account to a conformed `customer_id`.
`par30_ratio` is the lending metric, and `portfolio_par30` is its MetricFlow
exposure. The product spec is
[`docs/data_products/loan_month_end.md`](docs/data_products/loan_month_end.md).
Regenerate the checked-in CSVs from the scenario table, then check them against the contract:

```bash
python3 scripts/generate_lending_data.py --golden
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_source_contracts.py
```

`--seed` does not change the golden files. `--scale N` writes parquet under
`data/lending/`, which is git-ignored, and needs the DuckDB package already
installed in the dbt image.

## What is intentionally deferred

This repo is scoped as a lab rather than a full production platform.
Deferred items include live Metabase dashboards, recognized ARR reconciliation,
production orchestration, row-level security, currency conversion, usage-based
pricing, and historical type-2 account dimensions.
The ARR marts carry `currency_code`, and the only certified value is EUR.
Lending amounts are minor units, and the golden currency is EUR.

That boundary is deliberate: it keeps the case study focused on proving one metric deeply instead of spreading effort across too many unfinished surfaces.

## Quick Start

Prerequisite: a running Docker daemon.

```bash
docker compose build
make deps
docker compose run --rm dbt build
docker compose run --rm --entrypoint python dbt scripts/query_results.py
make governance-check
```

Expected certified Ending ARR:

```text
2025-01-31 | 19560.00
2025-02-28 | 21960.00
2025-03-31 | 30600.00
2025-04-30 | 30240.00
2025-05-31 | 25320.00
2025-06-30 | 25320.00
```

Inspect the local deployment:

```bash
make inspect
```

Generate and serve dbt docs at `http://localhost:8080`:

```bash
make docs
make docs-serve
```

Configure `.env` from `.env.example`, then validate and deploy to Snowflake:

```bash
make debug-prod
make build-prod
make deploy-snowflake-semantic-view
```

## Documentation

1. [`docs/evaluation_guide.md`](docs/evaluation_guide.md) for local and Snowflake verification.
2. [`docs/metric_contract_arr.md`](docs/metric_contract_arr.md) for the certified metric contract.
3. [`docs/singular_business_tests.md`](docs/singular_business_tests.md) for the human-readable test catalog.
4. [`docs/data_quality.md`](docs/data_quality.md) for the data-quality observability layer.
5. [`docs/governance_quality_gate.md`](docs/governance_quality_gate.md) for the manifest governance gate, and [`docs/architecture/conventions.md`](docs/architecture/conventions.md) for the rule ids.
6. [`docs/change_examples/exclude_paused_subscriptions.md`](docs/change_examples/exclude_paused_subscriptions.md) for the metric-change example.
7. [`models/snowflake_semantic/revenue_metrics.sql`](models/snowflake_semantic/revenue_metrics.sql) for the native Snowflake semantic view.
8. [`docs/ci_cd.md`](docs/ci_cd.md) for GitHub Actions validation and Snowflake deployment.
9. [`docs/adr/0004-loan-events-batch-vs-streaming.md`](docs/adr/0004-loan-events-batch-vs-streaming.md) and [`docs/adr/0005-synthetic-data-strategy.md`](docs/adr/0005-synthetic-data-strategy.md) for the lending batch and the synthetic-data tiers.
10. [`docs/data_products/loan_month_end.md`](docs/data_products/loan_month_end.md) for the loan month-end product, and [`docs/data_products/production_grade_checklist.md`](docs/data_products/production_grade_checklist.md) for the same checklist applied to ARR and to that fact.

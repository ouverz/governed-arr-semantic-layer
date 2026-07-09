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
- it does not prove a hosted dbt Semantic Layer query path locally; and
- it is intentionally scoped to one metric, not a broad analytics platform.

## Portfolio Highlights

- One governed metric, Ending ARR, defined end to end.
- Real ARR edge cases: billing intervals, discounts, exclusions, churn, reactivation, and renewals.
- A documented metric contract, singular business tests, and model/unit tests that prove the logic.
- Data-quality observability models around the ARR staging inputs.
- A governance quality gate that checks required metric-product controls.
- A documented metric-change example for excluding paused subscriptions prospectively.
- A governed consumption story that distinguishes certified BI and AI reuse from raw-table interpretation.
- A reproducible local build that reviewers can run with Docker only.

## Operating-model controls

The project includes a data-quality observability layer for completeness, validity, duplicates, freshness/coverage, and referential integrity across ARR staging inputs. It also includes a governance quality gate that checks required artifacts such as the metric contract, owners, certified grain, semantic model, fixtures, business tests, and CI validation.

See [`docs/data_quality.md`](docs/data_quality.md), [`docs/governance_quality_gate.md`](docs/governance_quality_gate.md), and [`docs/change_examples/exclude_paused_subscriptions.md`](docs/change_examples/exclude_paused_subscriptions.md).

The repo is structured like a hands-on lab, but the implementation goal is a
production-style operating model: explicit metric ownership, reviewed definition
changes, repeatable local validation, Snowflake deployment, and post-deploy
semantic checks.

## Selected visuals

These two views show the shape of the system without making the README a wall of text.

![ARR lineage and transformation layers](<images/Screenshot 2026-06-22 at 23.26.22.png>)

![ARR fact and test nodes](<images/Screenshot 2026-06-22 at 23.27.46.png>)

## Pattern borrowed from mature revenue stacks

The project follows a pattern used by stronger revenue analytics teams: keep raw inputs separate, derive historical truth with effective dates, and expose a clean consumption layer on top. In practice that means the ARR logic is anchored in point-in-time snapshot facts rather than current-state rows, so month-end truth stays stable and explainable. The same separation also makes it easier to publish a certified dataset for BI or semantic consumption without asking downstream users to interpret raw source tables directly.

## What is intentionally deferred

This repo is scoped as a lab rather than a full production platform.
Deferred items include live Metabase dashboards, recognized ARR reconciliation,
production orchestration, row-level security, multi-currency, usage-based
pricing, and historical type-2 account dimensions.

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
5. [`docs/governance_quality_gate.md`](docs/governance_quality_gate.md) for automated governance checks.
6. [`docs/change_examples/exclude_paused_subscriptions.md`](docs/change_examples/exclude_paused_subscriptions.md) for the metric-change example.
7. [`models/snowflake_semantic/revenue_metrics.sql`](models/snowflake_semantic/revenue_metrics.sql) for the native Snowflake semantic view.
8. [`docs/ci_cd.md`](docs/ci_cd.md) for GitHub Actions validation and Snowflake deployment.

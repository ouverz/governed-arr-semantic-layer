# Data-Quality Observability

This project uses dbt tests to fail builds when certified ARR logic breaks. It also exposes data-quality models as inspectable monitoring outputs.

The distinction is intentional:

- dbt tests answer whether a build should pass;
- data-quality models answer what the quality state is for the data feeding certified Ending ARR.

## Models

The DQ layer starts with ARR staging inputs:

- `dq_arr__completeness` checks required field population for subscriptions and subscription lines.
- `dq_arr__validity` checks date ranges, billing intervals, quantities, prices, discounts, currency, and status values.
- `dq_arr__duplicates` checks duplicate identifier risk across accounts, subscriptions, subscription lines, products, contracts, orders, and order lines.
- `dq_arr__freshness` reports fixture business-date coverage for the seed-based lab. It does not claim live ingestion freshness.
- `dq_arr__referential_integrity` checks whether the ARR input graph is connected across subscriptions, accounts, products, contracts, and order lines.
- `dq_arr__summary` rolls the component outputs into a compact quality status view.

## Status Logic

The local lab uses strict thresholds because the fixture data is controlled:

- required fields must be 100% complete;
- identifiers must be 100% unique;
- validity checks must produce zero invalid records;
- relationship checks must produce zero orphan records;
- fixture coverage must include the expected January through June 2025 reporting window.

Production deployments can relax thresholds through explicit configuration later, but this lab keeps standards strict so quality regressions are visible.

## Running the DQ Layer

```bash
docker compose run --rm dbt build --select tag:data_quality
```

The summary view is the fastest entry point:

```sql
select *
from dq_arr__summary;
```

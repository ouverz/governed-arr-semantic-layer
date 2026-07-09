# Evaluation Guide

This guide is for reviewers who want to understand, run, and verify the ARR
metric product without reading every model first.

## What to Evaluate

The project demonstrates a governed ARR operating model:

1. raw Salesforce-style fixture inputs are transformed through staging,
   intermediate, and marts layers;
2. certified Ending ARR is exposed from `fct_arr_snapshot`;
3. ARR movement analysis is exposed from `fct_arr_movement`;
4. data-quality monitoring is exposed through the `dq_arr__*` models;
5. metric governance is checked by `scripts/governance_check.py`; and
6. Snowflake consumption is represented by the native semantic view
   `ARR_LAB.SEMANTIC.REVENUE_METRICS`.

The core business scenario is a prospective ARR definition change: paused
subscriptions are excluded from certified Ending ARR from `2025-04-01` forward,
while earlier published periods remain unchanged.

## Architecture Flow

```text
Salesforce-style CSV seeds
  -> staging models
  -> intermediate ARR line logic
  -> marts
       fct_arr_snapshot
       fct_arr_movement
       dim_account
       dim_date
  -> semantic consumption
       dbt semantic model
       Snowflake native semantic view
  -> operating controls
       dbt tests
       data-quality summary views
       governance quality gate
       CI/CD deployment checks
```

This mirrors a hands-on-lab pattern, but the emphasis is production operating
discipline: certified definitions, explicit business ownership, validation,
and deployment checks.

## Local Evaluation

Prerequisite: Docker daemon running.

```bash
docker compose build
make deps
docker compose run --rm dbt build
make semantic-validate
make governance-check
make query
```

Expected `make query` output:

```text
2025-01-31 | 19560.00
2025-02-28 | 21960.00
2025-03-31 | 30600.00
2025-04-30 | 30240.00
2025-05-31 | 25320.00
2025-06-30 | 25320.00
```

## Business Scenario

The metric-change example is documented in
`docs/change_examples/exclude_paused_subscriptions.md`.

The important decision is that the definition change is prospective:

- before `2025-04-01`, previously certified ARR is preserved;
- from `2025-04-01`, paused subscriptions are excluded;
- the expected fixture impact is `1200.00` less Ending ARR in April, May, and
  June 2025 than the previous definition would have produced.

The behavior is validated by:

```bash
docker compose run --rm dbt test --select assert_policy_change_impact_expected
```

## Snowflake Evaluation

After configuring `.env` from `.env.example`, run:

```bash
make debug-prod
make build-prod
make deploy-snowflake-semantic-view
```

The deploy command installs dbt packages, deploys the Snowflake native semantic
view through the `Snowflake-Labs/dbt_semantic_view` materialization, and then
validates the semantic view output against the expected ARR fixture totals.

Use these Snowflake checks after deployment.

```sql
show views in schema ARR_LAB.MARTS;

show semantic views in schema ARR_LAB.SEMANTIC;

show semantic metrics in ARR_LAB.SEMANTIC.REVENUE_METRICS;
```

Validate certified ARR from the mart:

```sql
select
  snapshot_date,
  sum(ending_arr) as certified_ending_arr
from ARR_LAB.MARTS.FCT_ARR_SNAPSHOT
group by snapshot_date
order by snapshot_date;
```

Validate certified ARR through the native Snowflake semantic view:

```sql
select *
from semantic_view(
  ARR_LAB.SEMANTIC.REVENUE_METRICS
  dimensions arr.reporting_date
  metrics arr.certified_ending_arr
)
order by reporting_date;
```

Compare against the expected fixture:

```sql
select *
from ARR_LAB.RAW.EXPECTED_ENDING_ARR_AFTER_POLICY_CHANGE
order by snapshot_date;
```

Inspect the data-quality operating view:

```sql
select *
from ARR_LAB.DATA_QUALITY.DQ_ARR__SUMMARY
order by check_area, check_name;
```

## What Should Be Visible in Snowflake

The implementation should create or refresh:

- raw seed tables in `ARR_LAB.RAW`;
- staging views in `ARR_LAB.STAGING`;
- intermediate ARR models in `ARR_LAB.INTERMEDIATE`;
- certified marts in `ARR_LAB.MARTS`;
- data-quality views in `ARR_LAB.DATA_QUALITY`; and
- the native semantic view `ARR_LAB.SEMANTIC.REVENUE_METRICS`.

The ARR definition change is visible in mart totals, semantic-view totals, dbt
test results, docs, and the semantic view metric comments/AI instructions.

## Optional Future Enhancement

A useful next enhancement, inspired by Snowflake Cortex hands-on-lab patterns,
would be a small governed AI example that consumes certified ARR outputs rather
than raw tables. Good candidates:

- summarize monthly ARR movement drivers;
- explain expansion, contraction, churn, and reactivation by account segment;
- generate an executive ARR commentary from certified metric outputs; or
- classify account-level ARR movement narratives for follow-up.

That should remain optional until the core ARR operating model is stable. The
professional signal is that AI is downstream of governed metrics, not a shortcut
around them.

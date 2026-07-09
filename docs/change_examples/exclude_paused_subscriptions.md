# Metric Change Example: Excluding Paused Subscriptions from ARR

## Business Reason

Paused subscriptions should not contribute to certified Ending ARR because they do not represent active recurring value available for renewal, expansion, or retention analysis.

## Previous Definition

Subscriptions contributed ARR when their effective dates were active, their subscription lines were active at month end, the product was ARR eligible, and the subscription currency was EUR.

The previous definition did not explicitly exclude paused subscription status.

## New Definition

Paused subscriptions are excluded from certified Ending ARR from `2025-04-01` forward.

The effective date is controlled by:

```yml
arr_paused_subscription_exclusion_start_date: "2025-04-01"
```

## Backfill and Restatement Decision

This change applies prospectively from `2025-04-01`. Historical published values before the effective date are not restated.

That is the default operating model for business definition changes: preserve prior certified reporting unless the prior output was materially wrong and the business approves a restatement.

## Expected Impact

The controlled fixture adds one paused subscription that would have contributed `1200.00` Ending ARR from April 2025 onward under the previous definition.

The certified metric excludes that amount from April 2025 onward:

```text
2025-04-30 | 1200.00 excluded
2025-05-31 | 1200.00 excluded
2025-06-30 | 1200.00 excluded
```

`analysis/arr_policy_change_impact.sql` calculates the before/after monthly impact.

## Affected Assets

- `seeds/raw_salesforce_subscriptions.csv`
- `seeds/raw_salesforce_subscription_lines.csv`
- `models/staging/salesforce/_salesforce__models.yml`
- `models/marts/revenue/fct_arr_snapshot.sql`
- `analysis/arr_policy_change_impact.sql`
- `seeds/expected_ending_arr_after_policy_change.csv`
- `tests/assert_policy_change_impact_expected.sql`
- `docs/metric_contract_arr.md`

## Required Approvals

- RevOps approval for business definition
- Finance approval for reporting impact
- Data approval for implementation and release

## Release Note

From `2025-04-01`, paused subscriptions are excluded from certified Ending ARR. Prior certified periods are not restated.

## Validation Evidence

The change is validated by a fixture-backed singular test:

```bash
docker compose run --rm dbt test --select assert_policy_change_impact_expected
```

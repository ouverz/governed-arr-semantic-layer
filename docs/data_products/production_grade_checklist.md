# Production-grade checklist

The same checks for Ending ARR and for loan month-end v1. A row is met only when the evidence exists in the repo. Items this lab does not operate are marked that way. They are not counted as met.

## Interface

| Check | Ending ARR | Loan month-end v1 |
| --- | --- | --- |
| Grain is declared | Met. `meta.grain` on [`fct_arr_snapshot`](../../models/marts/revenue/_revenue__models.yml) and [`fct_arr_movement`](../../models/marts/revenue/_revenue__models.yml). | Met. `loan_id` × `month_end_date` on [`fct_loan_month_end`](../../models/marts/lending/_lending__models.yml) and in the [spec](loan_month_end.md). |
| Column contract enforced | Met. `contract.enforced: true` on both ARR facts. | Met. `contract.enforced: true` on version 1. |
| Version is explicit when the interface is meant to break loudly | Not met as a version. The facts are unversioned. `currency_code` was an additive column. A removed column warns and does not fail the build. See the [dbt 1.11 notes](../adr/0000-dbt-1.11-behaviour-notes.md). | Met. `latest_version: 1`. The node id is `fct_loan_month_end.v1`. |
| A monetary column carries `currency_code` | Met. Both facts. The only value is EUR. | Met. `outstanding_principal_minor` with `currency_code`. The only value is EUR. |
| Stored money matches the product rule | Met under a dated exception. Amounts stay `decimal(18,2)`. MNY-02 on both facts expires 2027-06-30. [ADR 0002](../adr/0002-money-representation.md). | Met. `bigint` minor units. |

## Correctness

| Check | Ending ARR | Loan month-end v1 |
| --- | --- | --- |
| Hand-calculated expected values | Met. [`assert_ending_arr_expected_totals`](../../tests/assert_ending_arr_expected_totals.sql) and the account and movement seeds. | Met. [`assert_loan_month_end_expected`](../../tests/assert_loan_month_end_expected.sql) against [`expected_loan_month_end`](../../seeds/expected_loan_month_end.csv). |
| One row per grain | Met. [`assert_snapshot_grain`](../../tests/assert_snapshot_grain.sql) and [`assert_movement_grain`](../../tests/assert_movement_grain.sql). | Met. [`assert_loan_month_end_grain`](../../tests/assert_loan_month_end_grain.sql). |
| The published balance matches its inputs | Met. Movement rows tie beginning, ending, and the movement amount in [`assert_arr_movements_expected`](../../tests/assert_arr_movements_expected.sql). | Met. [`assert_loan_ledger_reconciles`](../../tests/assert_loan_ledger_reconciles.sql). The fact's outstanding principal equals the sum of ledger principal deltas known at the same cutoff. |
| Balance is not negative | Met. [`assert_ending_arr_non_negative`](../../tests/assert_ending_arr_non_negative.sql). | Met. [`assert_loan_balance_non_negative`](../../tests/assert_loan_balance_non_negative.sql). |
| Late information is a declared rule with a test | Met. Paused subscriptions drop out from 2025-04-01 and earlier months stay as published. [`assert_policy_change_impact_expected`](../../tests/assert_policy_change_impact_expected.sql). | Met. Default cutoff is 5 days. [`assert_loan_late_posting_dpd_11`](../../tests/assert_loan_late_posting_dpd_11.sql) compiles the same month-end query at 3 days and requires 11 days past due on `LN_LATE_POSTED` at 31 March. |

## Operability

| Check | Ending ARR | Loan month-end v1 |
| --- | --- | --- |
| Freshness SLA is declared | Declared, not operated. `meta.freshness_sla` on both facts. | Declared, not operated. `meta.freshness_sla` says month-end plus 5 days. |
| Upstream data has an owner and a check before use | Met for the lab fixtures. Data-quality models in [`docs/data_quality.md`](../data_quality.md). There is no producer contract on the Salesforce seeds. | Met. [`contracts/sources/loan_events.yml`](../../contracts/sources/loan_events.yml) is validated in CI before dbt. Source freshness is declared and not run, because the book is a closed 2025 history. |
| CI builds the product | Met. [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) runs `dbt build`. | Met. The same build includes the fact, the expected-value test, the ledger reconciliation, and the 3-day cutoff test. |
| On-call | Declared, not operated. | Declared, not operated. `support_channel` is `data@arr-lab.example`. |
| Availability target | Declared, not operated. No uptime number. | Declared, not operated. `meta.availability` says so. |

## Ownership

| Check | Ending ARR | Loan month-end v1 |
| --- | --- | --- |
| Group, access, and owner | Met. Public `revenue` facts. Owner Data, business owner RevOps. | Met. Public `lending` fact. Owner Data, business owner Credit. Staging and the ledger are private to `lending`. |
| Conformed keys resolve | Met. `account_id` on both facts relates to [`dim_customer`](../../models/marts/core/dim_customer.sql). `product_family` on the snapshot is in [`dim_product`](../../models/marts/core/dim_product.sql) for `product_line = subscription` ([`assert_arr_snapshot_products_in_dim_product`](../../tests/assert_arr_snapshot_products_in_dim_product.sql)). | Met. `customer_id` relates to `dim_customer`. `product_id` relates to `dim_product`. |
| Consumers are real | Met. [`sem_arr.yml`](../../models/semantic/sem_arr.yml) and the Snowflake semantic view. | Met. [`sem_lending.yml`](../../models/semantic/sem_lending.yml) defines `par30_ratio`. [`portfolio_par30`](../../models/exposures.yml) depends on that metric and on `fct_loan_month_end`. |

# Loan month-end (v1)

Synthetic SME lending balances for the same Salesforce accounts as the ARR lab. This is not a lender's book and not a credit decision.

## Purpose

Publish outstanding principal and days past due for each loan at calendar month-end, using only what the lending system had committed by a declared cutoff after that month-end.

## Grain

`loan_id` × `month_end_date`. A loan appears from the month it is originated through the last month-end in `dim_date`. In the DuckDB lab that window is January through June 2025.

## Columns

| Column | Meaning |
| --- | --- |
| `customer_id` | Conformed customer from `dim_customer`. The source still sends Salesforce `account_id`. |
| `product_id` | `TERM_SME` or `RCF_SME`, from `dim_product`. |
| `currency_code` | EUR. |
| `outstanding_principal_minor` | Principal still outstanding, in minor units. |
| `days_past_due` | Calendar days from the earliest unpaid due date to the month-end. |
| `dpd_bucket` | `current`, `1_29`, `30_59`, `60_89`, `90_plus`. |
| `loan_status` | `current`, `delinquent`, `closed`, or `written_off`. |

## Knowledge rule

An event counts for a month-end when both are true:

- its effective date is on or before the month-end;
- its recorded date is on or before the month-end plus `loan_knowledge_cutoff_days`.

The var defaults to 5. `LN_LATE_POSTED` paid on 20 March and the system recorded it on 4 April. At 31 March with 5 days, the payment counts: outstanding principal is 100000 minor units and days past due are 0. The same month with 3 days excludes that posting: outstanding principal is 200000 and days past due are 11 (`1_29`, `delinquent`). `tests/assert_loan_late_posting_dpd_11.sql` compiles the month-end query at 3 days and expects that row. The checked-in expected seed is the 5-day book.

`LN_LATE_15` is different. That March instalment was paid on 1 April, so the payment had not taken effect by 31 March. The 5-day cutoff does not pull it back. 31 March is 15 days past due.

## How the numbers are produced

`int_lending__loan_ledger` is the only balance calculation. A disbursement and a revolving draw increase principal. A repayment decreases principal by `principal_minor`. Interest does not. A prepayment pays the remaining principal and cancels later instalments, including their unearned interest. A write-off decreases principal and does not also close the loan.

Days past due use the ledger's instalment rows. Superseded instalments are not due. Collected principal is applied oldest due date first. The count is 0 when the earliest unpaid due date is the month-end itself. After a closure or a write-off the fact reports 0 days past due, because principal outstanding is 0.

Status is derived from those ledger rows: `written_off` if a write-off is known, otherwise `closed` if a closure is known, otherwise `delinquent` when days past due are positive, otherwise `current`.

## Version and contract

Version 1, `latest_version: 1`, contract enforced. The relation alias is `fct_loan_month_end`. The node id is `fct_loan_month_end.v1`.

## Metric

`par30_ratio` is the certified lending metric. It is the share of outstanding principal with `days_past_due >= 30`, taken at the latest month-end in the query. Both the numerator and the denominator are non-additive over `month_end_date`, the same pattern as Ending ARR. A sum of the ratio across months is not a portfolio total.

dbt 1.11 will not parse a ratio unless those two inputs are metrics. `outstanding_principal` and `par30_outstanding_principal` exist for that reason. They are not certified on their own.

On the fixture, at the default 5-day cutoff:

| Month-end | 30+ principal | Outstanding principal | Ratio |
| --- | ---: | ---: | ---: |
| 2025-03-31 | 500000 | 2150000 | 500000/2150000 |
| 2025-05-31 | 200000 | 1100000 | 200000/1100000 |
| 2025-06-30 | 0 | 700000 | 0 |

`make semantic-validate` checks the metric shape and these three totals.

## Consumers

`portfolio_par30` is the MetricFlow exposure. It depends on `par30_ratio` and `fct_loan_month_end` v1. `meta.consumers` lists that exposure. There is no other consumer.

## Changelog

Corrections and definition changes follow [ADR 0006](../adr/0006-restatement-policy.md).

- v1. Published the month-end fact and `par30_ratio`. No prior version to restate.

## SLA

`freshness_sla` is "month-end, known at month-end plus 5 days, rebuilt on demand." `availability` and `support_channel` are declared. This lab does not operate them. See the checklist.

## What this does not claim

- The monthly rate on the fixtures is illustrative. It is not an APR.
- Days past due after write-off are 0 here. A risk report that freezes the last delinquent count would be a different version.
- `dim_customer` attributes other than the key are current-state. This fact does not use them.
- The published window is the lab month-end spine. `LN_ON_TIME` still has one instalment due in July, which is after June 2025.

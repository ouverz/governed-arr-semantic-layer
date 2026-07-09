# Governed ARR Project Extension Plan

**Goal:** Extend the existing `governed-arr-semantic-layer` project with the highest-value additions for Senior/Staff Analytics Engineering positioning.

**Core positioning:**

> A governed ARR metric product with business validation, data-quality observability, safe change management, semantic-layer consumption, and automated governance checks.

This plan assumes the existing project already includes the repo, visual case-study page, and long-form article.

---

## Executive Summary

Do **not** start a new portfolio project. The current ARR project is already strong. The best next move is to deepen it with controls that real analytics teams need around trusted metrics.

Prioritized phases:

1. **Data-quality observability models** — highest immediate value.
2. **Governance quality gate** — enforce project-level governance artifacts.
3. **Metric-change management example** — show how ARR changes safely.
4. **Optional NRR extension** — add one higher-order metric only after controls are done.
5. **README / portfolio polish** — make the value obvious to reviewers.

---

# Phase 1 — Data-Quality Observability Layer

## Goal

Add proper data-quality models inspired by the dbt Labs pattern from:

`models/hed/data_quality/`

The important idea is that these models produce **inspectable DQ outputs**, not only binary dbt test failures.

Existing dbt tests answer:

> Should the build fail?

DQ models answer:

> What is the quality state of the data feeding this certified metric?

## Why this is valuable

This strengthens the project from:

> I tested ARR.

To:

> I built an observable metric product where input quality, referential integrity, and certified outputs can be monitored.

That is a strong Analytics Engineering signal.

## Deliverables

Create:

```text
models/data_quality/
  _data_quality__schema.yml
  dq_arr__completeness.sql
  dq_arr__validity.sql
  dq_arr__duplicates.sql
  dq_arr__freshness.sql
  dq_arr__referential_integrity.sql
  dq_arr__summary.sql

docs/data_quality.md
```

Modify:

```text
README.md
```

Optionally add later:

```text
analysis/data_quality_snapshot.sql
```

---

## 1. `dq_arr__completeness.sql`

### Purpose

Monitor required-field completeness across ARR source inputs.

### Suggested checks

For `stg_salesforce__subscriptions`:

- missing `subscription_id`
- missing `account_id`
- missing `contract_id`
- missing `subscription_status`
- missing `start_date`
- missing `end_date`
- missing `currency`

For `stg_salesforce__subscription_lines`:

- missing `subscription_line_id`
- missing `subscription_id`
- missing `product_id`
- missing `line_start_date`
- missing `line_end_date`
- missing `billing_interval_months`
- missing `quantity`
- missing `list_unit_price`
- missing `net_amount_per_period`

### Output shape

```text
quality_dimension
source_model
total_records
required_fields_checked
missing_required_values
completeness_score
quality_status
```

Example:

```text
Record Completeness | subscription_lines | 14 | 9 | 0 | 100.0 | pass
```

---

## 2. `dq_arr__validity.sql`

### Purpose

Validate whether values are logically valid for ARR modeling.

### Suggested checks

- subscription `start_date <= end_date`
- line `line_start_date <= line_end_date`
- `billing_interval_months > 0`
- `quantity > 0`
- `list_unit_price >= 0`
- `discount_percent between 0 and 100`
- `net_amount_per_period >= 0`
- `currency = 'EUR'` for current MVP scope
- subscription status is one of `active`, `cancelled`, `expired`

### Output shape

```text
quality_dimension
source_model
total_records
invalid_date_ranges
invalid_billing_intervals
invalid_quantities
invalid_prices
invalid_discounts
invalid_currency_records
validity_score
quality_status
```

---

## 3. `dq_arr__duplicates.sql`

### Purpose

Expose duplicate risk across core business entities.

### Suggested checks

- duplicate accounts
- duplicate subscriptions
- duplicate subscription lines
- duplicate products
- duplicate contracts
- duplicate orders
- duplicate order lines

### Output shape

```text
quality_dimension
entity_name
total_records
unique_ids
duplicate_records
uniqueness_pct
quality_status
```

---

## 4. `dq_arr__freshness.sql`

### Purpose

Represent freshness honestly for a seed-based lab.

Because this repo uses dbt seeds, do **not** pretend this is live production freshness based on `current_timestamp()`.

Recommended framing:

> Freshness monitoring pattern for production source tables; local seed data has no ingestion timestamp, so this model reports fixture coverage dates rather than ingestion freshness.

### Suggested checks

- min/max subscription start date
- min/max subscription end date
- min/max line start date
- min/max line end date
- latest modeled snapshot date
- expected reporting window coverage

### Output shape

```text
quality_dimension
dataset
earliest_business_date
latest_business_date
latest_snapshot_date
coverage_status
notes
```

---

## 5. `dq_arr__referential_integrity.sql`

### Purpose

Show whether the ARR input graph is connected correctly before the certified metric is calculated.

This is especially relevant for the ARR project because it proves subscriptions, accounts, products, contracts, and order lines connect cleanly.

### Suggested checks

- subscription lines without subscriptions
- subscription lines without products
- subscriptions without accounts
- subscriptions without contracts
- order lines without subscription lines
- order lines without products
- contracts without accounts

### Output shape

```text
quality_dimension
relationship_name
child_model
parent_model
orphan_records
integrity_status
```

Example:

```text
Referential Integrity | subscription_lines_to_products | subscription_lines | products | 0 | pass
```

---

## 6. `dq_arr__summary.sql`

### Purpose

Create a simple rollup model that summarizes the DQ layer.

This is the model a reviewer or hiring manager can understand quickly.

### Output shape

```text
quality_area
quality_score
critical_issues
warning_issues
quality_status
```

Example:

```text
Completeness          | 100.0 | 0 | 0 | pass
Validity              | 100.0 | 0 | 0 | pass
Duplicates            | 100.0 | 0 | 0 | pass
Referential Integrity | 100.0 | 0 | 0 | pass
Freshness/Coverage    | 100.0 | 0 | 0 | pass
```

---

## Phase 1 Acceptance Criteria

- `dbt build --select tag:data_quality` succeeds.
- All DQ models are materialized as views.
- Each DQ model has a clear model description and column descriptions in `_data_quality__schema.yml`.
- `dq_arr__summary` gives a concise rollup of the data-quality state.
- `docs/data_quality.md` explains what each DQ model monitors and why it exists.
- README includes a short section linking the DQ layer to the governed metric story.

## Phase 1 Hiring Signal

> I know tests are not enough. A real analytics product also needs observable quality signals around the data feeding the metric.

---

# Phase 2 — Governance Quality Gate

## Goal

Add an automated project-level governance check.

This is different from the DQ models:

- DQ models inspect the **data**.
- Governance quality gate inspects the **project controls and artifacts**.

## Deliverables

Create:

```text
scripts/governance_check.py
docs/governance_quality_gate.md
```

Modify:

```text
.github/workflows/ci.yml
README.md
```

## Suggested checks

The script should verify:

| Check | Example artifact |
|---|---|
| Metric contract exists | `docs/metric_contract_arr.md` |
| Business owner declared | `Business owner: RevOps` |
| Technical owner declared | `Technical owner: Data` |
| Certified grain documented | `snapshot_date × account_id × subscription_id × product_family` |
| Invalid uses documented | “Do not use Ending ARR as GAAP revenue…” |
| Semantic model exists | `models/semantic/sem_arr.yml` |
| DQ layer exists | `models/data_quality/dq_arr__summary.sql` |
| Expected fixtures exist | `seeds/expected_ending_arr.csv` |
| Critical singular tests exist | `tests/assert_ending_arr_expected_totals.sql` |
| CI runs semantic validator | `scripts/validate_semantic_contract.py` |

## Example output

```text
Governance quality gate: PASSED

✓ Metric contract exists
✓ Business owner declared
✓ Technical owner declared
✓ Certified grain documented
✓ Invalid uses documented
✓ Semantic model exists
✓ Data-quality summary model exists
✓ Expected ARR fixture exists
✓ Critical ARR business tests exist
✓ CI runs semantic contract validation

Score: 10/10
```

## Phase 2 Acceptance Criteria

- `python scripts/governance_check.py` exits `0` when all checks pass.
- The script exits non-zero when a critical artifact is missing.
- CI runs the governance check.
- `docs/governance_quality_gate.md` explains each check in plain language.
- README explains the gate in 3–5 lines.

## Phase 2 Hiring Signal

> I can turn analytics governance standards into enforceable engineering controls.

---

# Phase 3 — Metric-Change Management Example

## Goal

Show how a certified metric changes safely when the business definition changes.

This is a high-value Senior/Staff AE addition because real organizations struggle more with metric evolution than with first-time metric creation.

## Recommended scenario

Use:

> Exclude paused subscriptions from certified Ending ARR.

Current seed data only has:

```text
active
cancelled
expired
```

So add one controlled paused-subscription case.

## Deliverables

Create:

```text
docs/change_examples/exclude_paused_subscriptions.md
analysis/arr_policy_change_impact.sql
seeds/expected_ending_arr_after_policy_change.csv
tests/assert_policy_change_impact_expected.sql
```

Modify:

```text
seeds/raw_salesforce_subscriptions.csv
seeds/raw_salesforce_subscription_lines.csv
models/staging/salesforce/_salesforce__models.yml
models/intermediate/revenue/int_subscription_arr_lines.sql
docs/metric_contract_arr.md
README.md
```

Possibly modify:

```text
models/semantic/sem_arr.yml
```

only if the semantic definition text needs updating.

## Change example doc outline

```md
# Metric Change Example: Excluding Paused Subscriptions from ARR

## Business reason
Paused subscriptions should not contribute to certified Ending ARR because they do not represent active recurring value.

## Previous definition
Subscriptions contributed ARR when their effective dates were active and their product was ARR eligible.

## New definition
Paused subscriptions are excluded from certified Ending ARR from 2025-04-01 onward.

## Expected impact
The policy change reduces certified Ending ARR by €X from April onward.

## Affected assets
- int_subscription_arr_lines
- fct_arr_snapshot
- fct_arr_movement
- sem_arr.yml
- expected ARR fixtures
- business tests

## Required approvals
- RevOps
- Finance
- Data

## Release note
From 2025-04-01, paused subscriptions are excluded from certified Ending ARR.
```

## Phase 3 Acceptance Criteria

- There is a clear before/after metric definition.
- Expected impact is calculated by SQL.
- A fixture-backed test proves the change was intentional.
- Docs explain approval and release process.
- README links to the change-management example.

## Phase 3 Hiring Signal

> I understand metric governance after launch — not just first implementation.

---

# Phase 4 — Optional NRR Extension

## Goal

Add one higher-order governed revenue metric built from certified ARR.

This should be done **after** DQ and governance controls, not before.

## Recommended metric

Add **Net Revenue Retention**, because it shows:

- reuse of certified ARR
- account-level movement logic
- cohort / retention thinking
- business interpretation

## Deliverables

Create:

```text
models/marts/revenue/fct_revenue_retention.sql
docs/metric_contract_nrr.md
seeds/expected_nrr_by_month.csv
tests/assert_nrr_expected.sql
```

Modify:

```text
models/marts/revenue/_revenue__models.yml
models/semantic/sem_arr.yml
README.md
```

## Definition

Simple portfolio wording:

> NRR measures how much recurring revenue was retained from an existing customer base after expansion, contraction, and churn.

Formula framing:

```text
NRR = retained ARR + expansion ARR - contraction ARR - churned ARR
      / starting ARR
```

## Phase 4 Acceptance Criteria

- NRR is derived from certified ARR / movement logic.
- NRR has its own metric contract.
- Expected NRR fixture exists.
- At least one singular test proves the expected result.
- Semantic layer or docs expose it as a governed revenue metric.

## Phase 4 Hiring Signal

> The certified ARR foundation supports higher-order revenue metrics instead of remaining a one-off model.

---

# Phase 5 — README and Portfolio Polish

## Goal

Make the new extensions understandable without forcing reviewers to inspect every file.

## Deliverables

Modify:

```text
README.md
docs/data_quality.md
docs/ci_cd.md
portfolio case study page
long-form writing article, optional
```

## README section to add

```md
## Extension: Data-quality and governance controls

This project includes an operational data-quality layer around the certified ARR metric. The DQ models monitor completeness, validity, duplicates, freshness/coverage, and referential integrity across the source and metric layers.

The project also includes a governance quality gate that checks whether the metric product has the required artifacts: metric contract, owner, grain, invalid uses, expected fixtures, semantic model, critical business tests, and CI validation.

Together, these additions show how a governed metric can be both technically validated and operationally monitored.
```

## Portfolio wording to add

> I extended the ARR metric product with a data-quality monitoring layer and automated governance checks. The project now demonstrates not only how to calculate a certified metric, but how to monitor the quality of the data behind it and enforce the controls required to keep the metric trustworthy.

## Phase 5 Acceptance Criteria

- README explains the DQ layer near the top.
- Portfolio page mentions the extension without becoming too long.
- Case study still has one clear message.
- The project is described as a governed metric product, not a generic data-quality demo.

---

# Final Prioritized Roadmap

## Priority 1 — Data-quality observability

Build proper DQ models around ARR inputs and certified outputs.

```text
models/data_quality/_data_quality__schema.yml
models/data_quality/dq_arr__completeness.sql
models/data_quality/dq_arr__validity.sql
models/data_quality/dq_arr__duplicates.sql
models/data_quality/dq_arr__freshness.sql
models/data_quality/dq_arr__referential_integrity.sql
models/data_quality/dq_arr__summary.sql
docs/data_quality.md
README.md update
```

## Priority 2 — Governance quality gate

Add automated checks that required governance artifacts exist.

```text
scripts/governance_check.py
docs/governance_quality_gate.md
.github/workflows/ci.yml update
README.md update
```

## Priority 3 — Metric-change management example

Show how certified ARR changes safely when the business definition changes.

```text
docs/change_examples/exclude_paused_subscriptions.md
analysis/arr_policy_change_impact.sql
seeds/expected_ending_arr_after_policy_change.csv
tests/assert_policy_change_impact_expected.sql
relevant model/seed/test updates
README.md update
```

## Priority 4 — Optional NRR extension

Add a second governed metric only after the controls are in place.

```text
models/marts/revenue/fct_revenue_retention.sql
docs/metric_contract_nrr.md
seeds/expected_nrr_by_month.csv
tests/assert_nrr_expected.sql
models/semantic/sem_arr.yml update
README.md update
```

---

# What Not To Do Now

Defer these unless there is a specific job target that makes them necessary:

| Idea | Reason to defer |
|---|---|
| Full payments reliability mart | Good idea, but becomes a second project |
| Multi-currency | Realistic, but can become messy and distract from governance |
| Usage-based pricing | Adds complexity without enough hiring signal right now |
| Row-level security | Useful, but less central to AE/revenue-metric positioning |
| Live dashboard | Nice visual, but lower value than governance/change-management proof |
| Large metric catalog | Makes the project broader but less sharp |

---

# Recommended Implementation Order

1. Add `models/data_quality/` with the six DQ models.
2. Add docs for the DQ layer.
3. Add `scripts/governance_check.py` and run it in CI.
4. Add the paused-subscription metric-change example.
5. Update README and portfolio copy.
6. Add NRR only if more depth is still needed.

---

# Final Positioning After Extensions

Do not describe the project as only:

> A governed ARR semantic-layer demo.

Describe it as:

> A governed revenue metric product in dbt and Snowflake, showing certified ARR, fixture-backed business validation, semantic-layer consumption, data-quality observability, automated governance checks, and safe metric-change management.

Shorter version:

> A governed ARR metric product showing how Analytics Engineering teams define, validate, monitor, and safely evolve trusted revenue metrics.

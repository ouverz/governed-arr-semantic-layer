# Governed ARR Operating Model Extension Plan

**Status:** Implemented through Phase 3  
**Scope:** Extend this repository through Phase 3, then stop and reassess.  
**Positioning:** Staff-level analytics engineering operating model for a governed revenue metric product.

This plan supersedes the broader `governed-arr-extension-plan.md` for active implementation. The original plan remains useful background, but the working scope is now deliberately capped at:

1. Data-quality observability layer
2. Governance quality gate
3. Metric-change management example

The repository should evolve from a single certified ARR metric demo into a compact operating model for how a production analytics team defines, validates, monitors, governs, and safely changes a certified metric.

## Strategic Direction

Keep this work in the existing repository.

The project already has the right foundation: seed fixtures, staging models, intermediate ARR logic, certified marts, model contracts, semantic assets, singular business tests, CI, and deployment documentation. Creating a separate repo would dilute the story unless the goal were a completely different domain. The stronger Staff-level signal is to show the lifecycle of one governed metric product in one coherent system.

The repo can broaden from "one metric deeply implemented" to "one metric product operated responsibly." That means adding controls around the existing ARR metric before adding more metrics.

## Audience and Documentation Shape

The implementation should be production-oriented rather than recruiter-oriented.

Primary repo docs should explain:

- what the system does;
- how to run it locally;
- how to deploy or validate it in Snowflake-oriented workflows;
- what controls exist around the metric; and
- how a metric definition change is handled.

Recruiter/hiring-manager material should come later as external or supplementary writing. The README should stay concise. More detailed explanation should live in purpose-built docs such as:

```text
docs/operating_model.md
docs/data_quality.md
docs/governance_quality_gate.md
docs/change_examples/exclude_paused_subscriptions.md
```

## Implementation Principles

- dbt tests remain the build-failing controls.
- Data-quality models are inspectable observability outputs, not a replacement for tests.
- The DQ layer starts with staging inputs only.
- DQ models should be views and selectable with `tag:data_quality`.
- The fixed seed coverage window remains `2025-01-01` through `2025-06-30` for now.
- README changes should be concise and link to deeper docs.
- CI should run both technical validation and governance validation.
- JSON output is useful for the governance gate if it stays simple.

## Reference Pattern

The DQ pattern is inspired by `dbt-labs/snowflake_sko_hol_2026`, where focused data-quality component models feed a dashboard-style data-quality view. That reference positions DQ as a monitorable analytical output, while tests remain the mechanism for failing builds.

For this project, the equivalent pattern should be:

```text
models/data_quality/
  dq_arr__completeness.sql
  dq_arr__validity.sql
  dq_arr__duplicates.sql
  dq_arr__freshness.sql
  dq_arr__referential_integrity.sql
  dq_arr__summary.sql
```

`dq_arr__summary` is the dashboard-style rollup model. It should give a compact status table across DQ areas so a reviewer, orchestrator, or BI surface can answer:

> What is the current quality state of the data feeding certified Ending ARR?

It should not be a vague scorecard. It should summarize concrete checks from the component DQ models.

Recommended output:

```text
quality_area
total_checks
passing_checks
warning_checks
failing_checks
quality_score
quality_status
```

Recommended status logic for the lab:

- `pass`: no failing checks and no warning checks;
- `warn`: at least one warning check and no failing checks;
- `fail`: at least one failing check.

Because this is a fixture-backed lab, thresholds can be strict at first:

- completeness target: `100%`;
- uniqueness target: `100%`;
- validity target: `100%`;
- referential integrity target: zero orphan records;
- freshness/coverage target: expected fixture date coverage is present.

If a later production deployment needs tolerance thresholds, add them through dbt vars rather than hardcoding relaxed standards into the lab.

## Phase 1: Data-Quality Observability Layer

**Goal:** Add monitorable DQ views around the ARR staging inputs.

Create:

```text
models/data_quality/_data_quality__schema.yml
models/data_quality/dq_arr__completeness.sql
models/data_quality/dq_arr__validity.sql
models/data_quality/dq_arr__duplicates.sql
models/data_quality/dq_arr__freshness.sql
models/data_quality/dq_arr__referential_integrity.sql
models/data_quality/dq_arr__summary.sql
docs/data_quality.md
```

Modify:

```text
dbt_project.yml
README.md
```

### Design

Start with staging models only:

```text
stg_salesforce__accounts
stg_salesforce__products
stg_salesforce__contracts
stg_salesforce__subscriptions
stg_salesforce__subscription_lines
stg_salesforce__orders
stg_salesforce__order_lines
```

This keeps the first DQ layer focused on input quality. Certified marts are already protected by contracts and singular business tests. Mart-level DQ can be added later if there is a clear monitoring use case.

### Materialization and Selection

Configure the folder as views with a DQ tag:

```yml
models:
  arr_semantic_layer_lab:
    data_quality:
      +materialized: view
      +schema: data_quality
      +tags: ["data_quality"]
```

Acceptance criteria:

- `dbt build --select tag:data_quality` succeeds.
- DQ models are views.
- Each model and column is documented in `_data_quality__schema.yml`.
- `dq_arr__summary` provides a compact rollup.
- `docs/data_quality.md` explains that DQ models are observability outputs, while tests are CI enforcement.
- README links to the DQ docs in a short operating-model section.

## Phase 2: Governance Quality Gate

**Goal:** Add an automated check that validates project governance artifacts.

Create:

```text
scripts/governance_check.py
docs/governance_quality_gate.md
```

Modify:

```text
Makefile
.github/workflows/ci.yml
README.md
```

### What "strict vs resilient" Means

The governance script can check artifacts in two ways:

- strict checks look for exact phrases, such as `Business owner: RevOps`;
- resilient checks verify the presence of a document, heading, YAML object, model, or concept without requiring identical prose.

Recommendation: use exact checks only where the value is meant to be controlled metadata, such as owner, status, certified grain, expected fixtures, and required file paths. Use resilient checks for narrative sections like invalid uses or change process so the docs can improve without breaking CI over harmless wording changes.

### Required Checks

The script should verify:

- metric contract exists;
- business owner is declared;
- technical owner is declared;
- certified grain is documented;
- invalid uses are documented;
- change process is documented;
- semantic model exists;
- DQ summary model exists;
- expected ARR fixtures exist;
- critical singular business tests exist;
- CI runs semantic validation;
- CI runs governance validation.

### Output

Default output should be human-readable.

Add `--json` if it stays simple:

```bash
python scripts/governance_check.py --json
```

Suggested JSON shape:

```json
{
  "status": "pass",
  "score": 12,
  "max_score": 12,
  "checks": [
    {
      "name": "metric_contract_exists",
      "status": "pass",
      "severity": "critical",
      "details": "docs/metric_contract_arr.md"
    }
  ]
}
```

### Local and CI Execution

Add a Make target:

```text
make governance-check
```

Run it in CI after semantic validation or immediately before it. The quality gate should exit non-zero when a critical check fails.

Acceptance criteria:

- `python scripts/governance_check.py` exits `0` when all required controls exist.
- The script exits non-zero when a critical artifact is missing.
- `python scripts/governance_check.py --json` returns valid JSON.
- `make governance-check` works locally.
- CI runs the governance check.
- `docs/governance_quality_gate.md` explains each check in plain language.
- README explains the gate briefly and links to the detailed doc.

## Phase 3: Metric-Change Management Example

**Goal:** Show how a certified metric changes safely after launch.

Use this scenario:

> Exclude paused subscriptions from certified Ending ARR from `2025-04-01` forward.

### Recommendation

Implement this as a real certified metric change, not only an isolated analysis example.

Reasoning:

In production, a business definition change normally needs an effective date, impact analysis, approval, release note, implementation, and tests. If the change is only placed under `analysis/`, the repo demonstrates impact analysis but not controlled metric evolution. For Staff-level positioning, the stronger signal is to show the full path from proposed policy change to tested production logic.

Do not restate all history unless the business explicitly approves a historical backfill. The default best practice is:

- define the effective date;
- quantify the forward-looking impact;
- preserve historical published values unless there is a material error or approved restatement;
- document whether downstream consumers should expect a discontinuity from the effective date.

For this lab, the policy should apply from `2025-04-01` onward.

### Subscription Status Handling

Add `paused` as an accepted subscription status as part of Phase 3. Do not add it earlier unless the seed data already contains paused subscriptions.

The logic should allow paused rows to exist, but exclude them from certified Ending ARR only from the policy effective date forward.

### Deliverables

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
models/marts/revenue/fct_arr_snapshot.sql
docs/metric_contract_arr.md
README.md
```

Potentially modify:

```text
models/semantic/sem_arr.yml
```

only if the semantic description needs to reflect the paused-subscription policy.

### Implementation Notes

Add one controlled paused-subscription case with ARR contribution that would affect April onward. The example should make the impact easy to inspect and test.

The implementation should make the effective-date policy explicit. Avoid burying it in prose only. Prefer a dbt var such as:

```yml
vars:
  arr_paused_subscription_exclusion_start_date: "2025-04-01"
```

The policy can then be referenced in SQL and documentation.

### Impact Analysis

`analysis/arr_policy_change_impact.sql` should show before/after ARR by month and the difference caused by excluding paused subscriptions.

Recommended output:

```text
snapshot_date
ending_arr_before_policy
ending_arr_after_policy
policy_impact_amount
```

### Documentation

`docs/change_examples/exclude_paused_subscriptions.md` should include:

- business reason;
- previous definition;
- new definition;
- effective date;
- backfill/restatement decision;
- expected impact;
- affected assets;
- required approvals;
- release note;
- validation evidence.

Acceptance criteria:

- Paused subscription status is represented in seed data.
- Staging tests accept `paused`.
- Certified ARR excludes paused subscriptions from `2025-04-01` onward.
- Impact analysis calculates the before/after difference.
- Fixture-backed test proves the policy impact.
- Metric contract documents the new policy and effective date.
- Change example doc explains approvals, release process, and restatement decision.
- README links to the change-management example without becoming long.

## Out of Scope for This Plan

Do not implement NRR in this phase of work.

NRR remains a good later extension, but only after the operating-model controls are complete. Adding NRR now would compete with the clearer story: trusted ARR, observable inputs, enforced governance, and safe metric change.

Also out of scope for this plan:

- portfolio page updates;
- long-form blog/article;
- hosted dashboard;
- production orchestration beyond CI examples;
- mart-level DQ beyond the summary needed for this operating model;
- tolerance-based DQ thresholds;
- multi-currency ARR;
- row-level security.

## Phase Tracking

Update this section as implementation progresses.

| Phase | Status | Notes |
|---|---|---|
| Phase 1: Data-quality observability | Complete | Added staging-model DQ views, `dq_arr__summary`, schema docs, and `docs/data_quality.md`. Validated with `dbt build --select tag:data_quality`. |
| Phase 2: Governance quality gate | Complete | Added `scripts/governance_check.py`, JSON output, `make governance-check`, CI wiring, and `docs/governance_quality_gate.md`. |
| Phase 3: Metric-change management | Complete | Added paused-subscription fixture, prospective exclusion from `2025-04-01`, impact analysis, fixture-backed policy test, and change-management docs. |

## Remaining Decisions

1. Decide whether `dq_arr__summary` should remain only under `models/data_quality` or whether a later dashboard-facing mart should also be added.
2. Decide whether governance check JSON should be saved as a CI artifact later.
3. Decide whether Phase 3 should include a lightweight release-note file in addition to the change example doc.
4. Decide whether to migrate legacy semantic YAML for dbt Fusion compatibility in a future cleanup.

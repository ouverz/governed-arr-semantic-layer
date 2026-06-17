# Executive Semantic Layer Interview Deck — v2

This version goes deeper on the ARR logic, the evidence behind it, and the governance tradeoffs.

## Slide 1 — One trusted ARR answer, ready for humans and AI
A semantic layer on top of the existing data platform
One governed metric, proven end to end

## Slide 2 — Why this project exists
Boards and RevOps do not need more dashboards.
They need one ARR answer that survives BI, finance review, and AI reuse.

The case study is not a platform survey. It is a proof that one important metric can be defined, certified, and consumed safely.

## Slide 3 — What the project actually proves
A single end-to-end ARR path from synthetic Salesforce-style inputs to:
- a certified month-end ARR fact
- an explainable ARR movement fact
- dbt semantic metrics
- a Snowflake semantic-view consumption path
- tests, contracts, and a repeatable demo runbook

## Slide 4 — The metric is the product
Ending ARR is not just a sum of active rows.
It is a governed business definition with:
- month-end certification
- effective-date logic
- eligibility rules
- annualization rules
- approved dimensions
- invalid uses
- a change process

## Slide 5 — ARR rules that make the project non-trivial
The MVP rules are explicit:
- calendar month-end only
- USD only
- annualize recurring lines with `net_amount_per_period × 12 / billing_interval_months`
- exclude one-time fees, services, credits, and tax
- use effective dates, not just current status
- preserve historical inclusion for cancelled or expired subscriptions

## Slide 6 — Why the data model is layered this way
Synthetic Salesforce CSV seeds feed staging views, then one intermediate ARR rule model, then certified marts, then semantic consumption.

That separation matters:
- staging cleans names and types
- intermediate owns business logic
- marts expose certified facts
- semantic layers expose approved meaning

## Slide 7 — What the business logic model does
`int_subscription_arr_lines` is the calculation boundary.
It joins subscription lines, subscriptions, and products to determine:
- whether a line is ARR-eligible
- how much ARR it contributes
- whether the line should stay visible for auditability

Ineligible lines are not deleted. They remain inspectable with `is_arr_eligible = false` and `line_arr = 0`.

## Slide 8 — How we know the metric is correct
The repo does not rely on one validation method.
It uses a stack:
- hand-calculated expected totals
- singular business tests
- schema tests and model contracts
- unit tests for the complex logic
- semantic validation / contract checks

That is what makes the metric reviewable instead of merely runnable.

## Slide 9 — The edge cases are the point
The synthetic dataset was designed around real ARR scenarios:
- monthly, quarterly, and annual billing
- discounts
- one-time and services exclusions
- subscription start and end boundaries
- churn and reactivation
- renewal uplift
- multiple eligible lines at one grain

This is what keeps the project from feeling like a toy example.

## Slide 10 — Ownership and change control
The contract is as important as the SQL.
- RevOps owns the business meaning
- Data owns implementation and reliability
- changes require review, effective date handling, and re-certification

That avoids a common failure mode: the metric changes quietly while the dashboard still looks “correct.”

## Slide 11 — Why the semantic layer matters
The semantic layer is the control point that stops every consumer from rebuilding ARR differently.

It is also where the project surfaces a real architectural tradeoff:
- dbt provides lineage, governance, and testing
- Snowflake semantic views provide a governed consumption path for BI and AI

One certified definition should serve both.

## Slide 12 — AI should only see certified meaning
The AI story is intentionally constrained.
AI must read:
- certified metrics only
- approved dimensions only
- lineage-aware objects only
- verified queries or semantic surfaces only

The goal is not a free-form assistant over raw tables.
The goal is a controlled consumer of trusted business meaning.

## Slide 13 — What remains open by design
The project is strong, but it is still scoped as a lab.
Still deferred:
- live Metabase deployment
- live Snowflake semantic execution in this workspace
- recognized ARR and reconciliation
- multi-currency and historical type-2 account dimensions
- production ingestion through true warehouse sources

That scope boundary is intentional; it keeps the case study credible.

## Slide 14 — Success criteria
The deck succeeds if a reviewer can say:
- I understand the ARR contract
- I can see how the model is validated
- I know who owns the metric
- I understand why the semantic layer is needed
- I can see how AI would safely consume it

If the answer changes by surface, the model is not finished.

## Closing Thought
The point is not to create another abstraction.
The point is to create one shared business vocabulary that humans trust and AI can safely use.

# ADR 0006: When a published number is restated

## Status

Accepted.

## Context

Two different events can change a number that was already published. A payment amount in the batch can be wrong, and a later file corrects it. Or the definition of the number can change, as it did when paused subscriptions left Ending ARR. Those are not the same decision. One repairs a fact. The other changes what the fact means.

The loan month-end fact makes the difference concrete. `loan_knowledge_cutoff_days` is 5, so the 4 April posting is included in 31 March. Moving that cutoff to 3 days changes 31 March from current to 11 days past due. That is a different definition, not a correction of a wrong payment.

## Options

1. Always restate. Every change rewrites history. Consumers cannot tell a correction from a new rule, and a certified month can move without a version.
2. Never restate. A wrong payment stays wrong. The ledger cannot be the source of the balance if a corrected event is ignored.
3. Rule-based. A correction of wrong data restates the affected periods and is written down. A definition change applies from an effective date, or it ships as a new version. Certified history does not move silently.

## Decision

Option 3.

A data correction restates. The lending contract already says a correction is a new `event_id`, or a redelivered file after notice, not a silent overwrite. Rebuilding `fct_loan_month_end` for the affected month-ends is the restatement. The product spec's changelog records what changed, which periods, and why.

A definition change does not restate by default. It applies prospectively, or it is a new version of the fact or of `par30_ratio`. The precedent is paused subscriptions: they leave Ending ARR from 2025-04-01 forward, and months before that date stay as published. See `docs/change_examples/exclude_paused_subscriptions.md`.

Changing `loan_knowledge_cutoff_days`, the days-past-due count, or which balances enter `par30_ratio` is a definition change. It is not a restatement of March.

## Consequences

The changelog in `docs/data_products/loan_month_end.md` is the place a correction or a prospective change is written down. The source contract's additive-versus-breaking table still governs the batch payload. This ADR governs what happens to a number that was already published. It does not claim a closed accounting period is locked by a system of record. The lab rebuilds from the fixtures.

## Revisit when

A certified consumer requires every definition change to rewrite history, or forbids restatement of a month that has already been published.

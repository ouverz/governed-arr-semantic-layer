# ADR 0004: Loan events as a daily batch

## Status

Accepted.

## Context

The lending fixtures need a feed of applications, loan lifecycle events, schedule rows, and cash postings. The consumers that will sit on that feed are a month-end portfolio fact and, later, monthly features and a monthly decision. None of those act inside the day. The feed still has to show a posting that took effect in March and was committed in April. That gap is the late-posted scenario, and it disappears if the only timestamp is "when the file arrived".

## Options

1. A daily batch file per dataset, with an idempotency key and `recorded_at` on every row.
2. Change data capture from the loan database. Lower latency, and a capture process. This lab has no loan database to capture.
3. An event stream. The same latency argument, plus a broker to run.

## Decision

Option 1. `contracts/sources/loan_events.yml` sets `delivery.mode: daily_batch`, idempotency key `event_id`, and `effective_at <= recorded_at <= _loaded_at`. The dbt source declares freshness of 24 hours to warn and 36 hours to error on `_loaded_at`. `scripts/validate_source_contracts.py` checks the files before dbt.

The batch is the transport. The grain is the bitemporal event. A later capture feed or stream would land the same columns. A month-end model would not grow a second clock.

## Consequences

CI does not run `dbt source freshness`. The golden book is a closed 2025 history, so a freshness check against the wall clock fails because the newest `_loaded_at` is in 2025, not because a batch is late. The validator checks that `_loaded_at` is present and ordered instead. This ADR does not claim a scheduler or a notification inbox. The notice windows (one business day for an additive change, 60 days for a breaking change, and a notice before a restatement) are terms in the contract.

The answer flips when a consumer has to act inside the day: real-time underwriting, intraday collections, or a limit change that must be visible before the next batch. Until one of those exists, a stream adds a broker and does not change a number.

## Revisit when

A consumer decision is made on data newer than the previous batch, or a posting has to be visible before the 06:00 UTC file.

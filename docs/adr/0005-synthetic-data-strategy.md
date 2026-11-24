# ADR 0005: Two-tier synthetic lending data

## Status

Accepted.

## Context

The ARR lab's strongest check is a hand-calculated expected value. Lending needs the same kind of check for balances, days past due, and a late posting. It also needs a way to make a large file without checking that file in. Random rows cannot be an expected-value fixture. A hand-typed CSV of every column is hard to regenerate when a column is added.

## Options

1. Random rows from a fake-data library. Fast to grow, and impossible to hand-check.
2. Only hand-written seeds. Reviewable, and painful to scale or to add a column.
3. A readable scenario table, compiled by a deterministic generator. The golden CSVs are checked in. A scale mode writes parquet that is not checked in.

## Decision

Option 3. `scripts/lending_scenarios.py` is the golden table: eight named loans, the Salesforce `account_id` values, integer minor units, and both timestamps. `scripts/generate_lending_data.py --golden` rewrites `seeds/lending/` from that table. `--seed` does not change that output. `--scale N` uses `--seed` and writes parquet under `data/lending/`, which is git-ignored. Scale account ids look like `S000001` and are not Salesforce accounts, so a volume file cannot be mistaken for the cross-product book.

Generation and the CSV path use the Python standard library. Parquet is written with DuckDB, which the project image already installs. The standard library has no parquet writer. A separate parquet library would be a dependency for a file that is not committed.

The golden book is eight loans and under 200 rows. Interest is an illustrative simple monthly rate (`opening principal * monthly_rate_bps // 10000`), not an APR. Prepayment charges remaining principal and cancels unearned interest. A write-off removes remaining principal and does not capitalise unpaid interest. Days past due, when a later fact computes it, counts calendar days from the earliest unpaid due date and is 0 on the due date itself.

## Consequences

A reviewer can recompute a scenario from the table and diff the CSV. Scale data has no expected values and must not be used as one. This ADR does not claim the rows are a lender's book, or that the rate is a price.

## Revisit when

A hand-checked case is not one of the eight scenarios, or a volume test needs a file format DuckDB cannot write.

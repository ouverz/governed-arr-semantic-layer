# ADR 0002: Money representation

## Status

Accepted.

## Context

Ending ARR is stored as `decimal(18,2)` with no currency column. The EUR-only rule is a filter in `int_subscription_arr_lines`. A second product, especially one fed by payments or a ledger, will not want a floating decimal as the stored amount, and a consumer cannot see the currency from the mart.

## Options

1. `decimal(18,2)` on every model. This matches ARR today. Sums of decimals can drift, and the currency stays implicit.
2. Integer minor units and `currency_code` from staging through facts and the semantic layer. Correct for ledgers. It rewrites ARR, its expected-value fixtures, and the semantic contract for no change in the certified numbers.
3. Integer minor units in sources, staging, and facts. Convert to decimal only in the semantic or presentation layer, once, using the currency exponent. ARR keeps `decimal(18,2)` as a dated exception and gains `currency_code`.

## Decision

Option 3. Public models that expose a monetary amount must include `currency_code` (MNY-01). The amount itself is an integer minor-unit type unless `governance/exceptions.yml` lists the model under MNY-02. `fct_arr_snapshot` and `fct_arr_movement` are exempt from MNY-02 until 2027-06-30 and now carry `currency_code = 'EUR'`. The column is additive. Ending ARR values and the expected-value seeds are unchanged. Rounding, if a presentation layer divides by the currency exponent, is not stored.

`currency_code` on the ARR facts is restricted to `EUR` by an accepted-values test. That is the current metric scope, not a permanent single-currency warehouse.

## Consequences

A lending fact can store `outstanding_principal_minor` as `bigint` plus `currency_code` and pass MNY-01 and MNY-02 with no gate change. ARR consumers keep the decimal they already use. The exception is visible in the gate output and expires. Staging ARR amounts are still decimal; the enforced boundary is the public mart, which is what a consumer reads. This ADR does not claim multi-currency conversion exists.

## Revisit when

A consumer of Ending ARR needs minor units, a second currency is in the certified metric, or the MNY-02 exception reaches its expiry without being renewed.

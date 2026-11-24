# ADR 0001: Serving layers

## Status

Accepted.

## Context

The lab currently serves one certified metric, Ending ARR, from public marts and two semantic surfaces (MetricFlow and a Snowflake semantic view). Later work may add entity-grain facts for another product, feature tables, and a decision model. Those are different promises. A metric definition, a sliceable fact, a model feature, and a decision do not belong in one table or one contract.

## Options

1. Put every consumer-facing output in the semantic layer. BI, training sets, and decisions all query metrics. Feature history and decision inputs are awkward as metrics, and the semantic layer is the wrong place for a row-level contract.
2. Put every consumer-facing output in public marts. Metrics get redefined in every dashboard. There is no single place a definition is certified.
3. Split by the job of the table. Metrics with a business definition go to the semantic layer. Entity-grain facts for BI and ad hoc use are public marts. Model and decision inputs are versioned feature tables and are not a BI surface. Decisions are dbt models pinned to a feature version.

## Decision

Option 3. Ending ARR stays a semantic metric on top of `fct_arr_snapshot`. The fact remains the public, contracted mart. Feature tables and decision models are not built in this change. The layer prefixes in `governance/policy.yml` (`fct_`, `dim_`, `feat_`, `dec_`, `ml_`) reserve the names so those layers can be added without a new gate.

## Consequences

A reviewer can tell from the model name and the layer which contract applies. BI is not pointed at a feature table. The semantic layer is not asked to store a training row. This ADR does not create those tables, and it does not claim a hosted semantic layer is running in the local lab.

## Revisit when

A consumer needs a feature or a decision that cannot be expressed as a versioned model in this project, or a metric that analysts must compute from a feature table because the semantic layer cannot express it.

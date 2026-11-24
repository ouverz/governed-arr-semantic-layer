# ADR 0003: One project, ownership by group

## Status

Accepted.

## Context

The repo is one dbt project, `arr_semantic_layer_lab`, on synthetic data. A second product needs an owner and a boundary so its private models are not a free dependency for someone else's mart. Splitting repos or projects would also split the join a cross-product question needs.

dbt 1.11 does not accept a `groups:` block in `dbt_project.yml`. Group definitions belong in a properties file. `access: private` is enforced: a node may reference a private model only when it has the same group. Singular tests pick up `group` from `data_tests:` in `dbt_project.yml`. Analyses did not pick up a project-level `analyses:` group in the 1.11.11 spike, so each analysis sets `group` in `config()`. Unit tests have no `group` field. A full `dbt build` still passed with private staging, because unit-test inputs are not rejected the way model refs are. See `docs/adr/0000-dbt-1.11-behaviour-notes.md`.

## Options

1. One repo and one project. Ownership is a dbt group. `private` models are usable inside the group. `public` models are the cross-group interface. The project display name stays the ARR lab until a second product exists.
2. A sibling repo per product. The cross-product join becomes an export, and a convention change is a change in two places.
3. Two projects plus cross-project `ref`. That needs dbt Mesh or another package. The lab does not have dbt Cloud, and the join would be the thing under test.

## Decision

Option 1. Groups `revenue`, `lending`, `credit_risk`, and `platform` are declared in `models/_groups.yml`. ARR staging, intermediate, and data quality are `private` in `revenue`. ARR facts and `dim_account` are `public` in `revenue`. `dim_account` stays in `revenue` because it selects private Salesforce staging; it is not yet a conformed customer. `dim_date` and `metricflow_time_spine` are `public` in `platform`. Current singular tests are `revenue`, because every test in `tests/` is an ARR test. A lending test that reads private lending models has to override `+group` to `lending`.

The warehouse for this lab stays DuckDB, with the existing Snowflake parse in CI. A second warehouse would show that SQL parses, not that the ownership boundary holds.

## Consequences

A public platform model can be referenced from any group. A private revenue model cannot. The gate checks that the manifest group is one of the four names and that access matches the layer. Adding lending is a properties change: group, access, contract, tests, and meta. This ADR does not rename the repository, does not add a second product, and does not claim a staffed owner. `data@arr-lab.example` is a lab role.

## Revisit when

Two products need different deploy cadences or different teams, or a private model must be shared across groups often enough that `protected` would be the honest access. Those are the triggers for a second project, not a second folder.

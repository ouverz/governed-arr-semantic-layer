# Governance quality gate

The governance gate checks every enabled model in `target/manifest.json` against `governance/policy.yml`. It is a control on the project graph, not a linter for markdown wording.

Data-quality models inspect rows. This gate inspects naming, layer, group, access, ownership, grain, contracts, money, time, status vocabularies, and descriptions. The rule ids and the model that already follows each one are in [`docs/architecture/conventions.md`](architecture/conventions.md).

Exceptions are listed in `governance/exceptions.yml` with an owner and an `expires_on` date. An expired exception fails the gate (`EXC-01`) and no longer hides the underlying rule. The ARR decimal amounts are the current MNY-02 exception. `metricflow_time_spine` is the current naming exception.

## Running locally

The manifest has to exist first.

```bash
make build
make governance-check
make governance-test
```

JSON, a markdown file, and every passing check:

```bash
python3 scripts/governance_check.py --json
python3 scripts/governance_check.py --markdown /tmp/governance.md --verbose
```

The command exits non-zero when any check fails.

Removing `meta.owner` from a public model fails with `OWN-01` and the model name. CI does that against the built manifest and requires the failure. The unit tests in `tests/governance/` cover the same rule with a manifest that is not the ARR project, including a lending-shaped model that passes on metadata alone.

## What this gate does not do

It does not check seeds, singular test SQL, or semantic metric definitions. Semantic definitions stay with `make semantic-validate`. It does not see models that are disabled in the manifest it was given. On DuckDB that includes `revenue_metrics`. It does not require an exposure. Exposures are added with a real consumer, not a placeholder.

# Governance Quality Gate

The governance quality gate checks whether the ARR metric product has the artifacts needed to operate as a certified metric, not just a working SQL model.

Data-quality models inspect data. The governance gate inspects project controls.

## Checks

The gate validates that:

- the Ending ARR metric contract exists;
- business and technical owners are declared;
- the certified grain is documented;
- invalid uses are documented;
- the metric change process is documented;
- the semantic model exists;
- the data-quality summary model exists;
- expected ARR fixtures exist;
- critical singular business tests exist;
- CI runs semantic validation;
- CI runs governance validation.

Some checks are exact because the metadata should be stable. For example, owner declarations and required file paths are treated as controlled artifacts. Narrative sections are checked more flexibly so documentation can improve without breaking CI over harmless wording changes.

## Running Locally

```bash
make governance-check
```

For JSON output:

```bash
python3 scripts/governance_check.py --json
```

The command exits non-zero when a critical governance control is missing.

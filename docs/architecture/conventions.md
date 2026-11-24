# Cross-product conventions

These rules are what `make governance-check` enforces from `governance/policy.yml`. A model that breaks a rule fails the build. A rule marked review-only is not a CI failure. Dated exceptions live in `governance/exceptions.yml` and stop applying on `expires_on`.

A second product passes the same gate by setting group, access, contract, tests, and `meta`. The gate's code does not name that product.

| ID | Rule | Example | Enforced by |
| --- | --- | --- | --- |
| NAM-01 | Prefix by layer: `stg_`, `int_`, `fct_`/`dim_`, `dq_`, `feat_`, `dec_`, `ml_`, `sem_` | `stg_salesforce__accounts` | `name_prefix` |
| LAY-01 | The file lives under that layer's directory | `models/marts/revenue/fct_arr_snapshot.sql` | `known_layer` |
| GRP-01 | `group` is one of `revenue`, `lending`, `credit_risk`, `platform` | `fct_arr_snapshot` is `revenue` | `group_allowed` |
| ACC-01 | Staging, intermediate, and data quality are `private`. Marts, features, decisioning, and ML are `public` | `fct_arr_movement` is `public` | `access_matches_layer` |
| OWN-01 | Every model sets `meta.owner` | `Data` on `dim_date` | `required_meta` |
| OWN-02 | Public models set `meta.business_owner` | `RevOps` on `fct_arr_snapshot` | `required_meta` |
| TIR-01 | Public `meta.tier` is `certified` or `supporting` | `fct_arr_snapshot` is `certified` | `required_meta` |
| GRN-01 | Public models state `meta.grain` | snapshot grain on `fct_arr_snapshot` | `required_meta` |
| GRN-02 | A single-column grain has a `unique` test. A composite grain has a test whose name contains `grain` | `assert_snapshot_grain`, `assert_movement_grain` | `grain_test` |
| SLA-01 | Public models set `meta.freshness_sla` | month-end fixture text on the ARR facts | `required_meta` |
| KEY-01 | Public `meta.primary_key` columns exist and are `not_null` | `account_id` on `dim_account` | `primary_key` |
| KEY-02 | `account_id` is `key_role: salesforce_account`. `customer_id` is `key_role: conformed_customer` | `dim_account.account_id` | `key_role` |
| CTR-01 | Layers marked `contract: true` enforce a typed contract | both ARR facts, `dim_account`, `dim_date` | `contract` |
| MNY-01 | A public model with a monetary amount has `currency_code` and a `not_null` test | `fct_arr_snapshot.currency_code` | `currency_column` |
| MNY-02 | Those amounts are integer minor units unless a dated exception says otherwise | ARR facts are exempt until 2027-06-30 | `money_type` |
| TIM-01 | `*_date` and `date_day` are `date`. `*_at` is a timestamp. Checked when the type is declared, and always on a contract | `snapshot_date`, `date_day` | `temporal_type` |
| STS-01 | `status`, `*_status`, `movement_type`, `dpd_bucket`, and `loan_status` have `accepted_values` | `movement_type` on `fct_arr_movement` | `accepted_values` |
| GEO-01 | `country_code`, when present, is a string with `meta.geo_standard: iso_3166_1_alpha_2` | no current model; the lending-shaped gate test covers it | `column_meta` |
| DOC-01 | Every model has a description | `fct_arr_snapshot` | `description` |

## Keys, money, time, status

`account_id` is the Salesforce account. It is not a cross-product customer key. A later conformed customer uses `customer_id` and `key_role: conformed_customer`. `dim_account` stays in the `revenue` group because it is built from private Salesforce staging.

Money on a public model is an integer minor-unit amount plus `currency_code` (ADR 0002). Ending ARR and its movements keep `decimal(18,2)` under MNY-02 and still carry `currency_code = EUR`. The singular expected-value fixtures are unchanged. Upstream ARR staging still stores decimal amounts and a `currency` column; MNY-01 and MNY-02 apply to public models, which is the interface a consumer sees.

`*_date` is a business date. `*_at` is a UTC timestamp. `effective_at` and `recorded_at` are the pair a later bitemporal model uses. The gate checks declared types, not the values.

Status vocabularies are the `accepted_values` list on the column. ARR movements use `new`, `expansion`, `contraction`, `churn`, `reactivation`. Data-quality flags use `pass`, `fail`, and `warn` on the summary.

## Review-only

- **EXP-01.** Public models gain an exposure when a real consumer exists in the repo. There is no exposure requirement yet, and no placeholder consumer.
- **Composite uniqueness SQL** beyond GRN-02's name check. `assert_snapshot_grain` and `assert_movement_grain` are the ARR evidence.
- **Upstream ARR decimals.** Staging and intermediate amounts are outside MNY-02. The public mart is the enforced boundary.
- **Snowflake semantic view.** `revenue_metrics` is disabled on DuckDB, so this gate does not see it. Its name is a dormant NAM-01 exception for a manifest where the model is enabled. Semantic metric definitions are checked by `make semantic-validate`.
- **Geography values.** GEO-01 checks the column contract, not that every code is a real ISO country.

## How to run

```bash
make build
make governance-check
make governance-test
```

`make governance-check` reads `target/manifest.json`. It exits non-zero when any check fails. `--json` prints every result. `--verbose` prints passes as well as failures and exemptions. In GitHub Actions the markdown table is appended to the step summary.

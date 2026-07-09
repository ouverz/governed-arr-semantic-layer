{{ config(enabled=target.type != 'snowflake') }}

with eligible_lines as (
    select *
    from {{ ref('int_subscription_arr_lines') }}
    where is_arr_eligible
),

month_ends as (
    select snapshot_date
    from {{ ref('dim_date') }}
),

before_policy_active_lines as (
    select
        month_ends.snapshot_date,
        eligible_lines.line_arr
    from eligible_lines
    inner join month_ends
        on eligible_lines.subscription_start_date <= month_ends.snapshot_date
        and eligible_lines.subscription_end_date >= month_ends.snapshot_date
        and eligible_lines.line_start_date <= month_ends.snapshot_date
        and eligible_lines.line_end_date >= month_ends.snapshot_date
),

before_policy as (
    select
        snapshot_date,
        cast(sum(line_arr) as decimal(18, 2)) as ending_arr_before_policy
    from before_policy_active_lines
    group by 1
),

after_policy as (
    select
        snapshot_date,
        cast(sum(ending_arr) as decimal(18, 2)) as ending_arr_after_policy
    from {{ ref('fct_arr_snapshot') }}
    group by 1
),

actual as (
    select
        coalesce(before_policy.snapshot_date, after_policy.snapshot_date) as snapshot_date,
        before_policy.ending_arr_before_policy,
        after_policy.ending_arr_after_policy,
        cast(
            before_policy.ending_arr_before_policy
            - after_policy.ending_arr_after_policy
            as decimal(18, 2)
        ) as policy_impact_amount
    from before_policy
    full outer join after_policy
        on before_policy.snapshot_date = after_policy.snapshot_date
),

expected as (
    select
        cast(snapshot_date as date) as snapshot_date,
        cast(expected_ending_arr_before_policy as decimal(18, 2))
            as expected_ending_arr_before_policy,
        cast(expected_ending_arr_after_policy as decimal(18, 2))
            as expected_ending_arr_after_policy,
        cast(expected_policy_impact_amount as decimal(18, 2))
            as expected_policy_impact_amount
    from {{ ref('expected_ending_arr_after_policy_change') }}
)

select
    coalesce(actual.snapshot_date, expected.snapshot_date) as snapshot_date,
    actual.ending_arr_before_policy,
    expected.expected_ending_arr_before_policy,
    actual.ending_arr_after_policy,
    expected.expected_ending_arr_after_policy,
    actual.policy_impact_amount,
    expected.expected_policy_impact_amount
from actual
full outer join expected
    on actual.snapshot_date = expected.snapshot_date
where actual.snapshot_date is null
    or expected.snapshot_date is null
    or abs(
        actual.ending_arr_before_policy
        - expected.expected_ending_arr_before_policy
    ) > 0.01
    or abs(
        actual.ending_arr_after_policy
        - expected.expected_ending_arr_after_policy
    ) > 0.01
    or abs(
        actual.policy_impact_amount
        - expected.expected_policy_impact_amount
    ) > 0.01

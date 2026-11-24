{{ config(group='lending') }}

with at_three_days as (
    {{ loan_month_end_query(3) }}
),

march as (
    select
        outstanding_principal_minor,
        days_past_due,
        dpd_bucket,
        loan_status
    from at_three_days
    where loan_id = 'LN_LATE_POSTED'
        and month_end_date = cast('2025-03-31' as date)
)

select
    outstanding_principal_minor,
    days_past_due,
    dpd_bucket,
    loan_status
from march
where outstanding_principal_minor != 200000
    or days_past_due != 11
    or dpd_bucket != '1_29'
    or loan_status != 'delinquent'

union all

select
    cast(null as bigint) as outstanding_principal_minor,
    cast(null as integer) as days_past_due,
    cast(null as varchar) as dpd_bucket,
    cast(null as varchar) as loan_status
where not exists (select 1 from march)

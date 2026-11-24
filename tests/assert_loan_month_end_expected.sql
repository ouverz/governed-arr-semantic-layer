{{ config(enabled=target.type != 'snowflake') }}

with actual as (
    select
        loan_id,
        month_end_date,
        customer_id,
        product_id,
        currency_code,
        outstanding_principal_minor,
        days_past_due,
        dpd_bucket,
        loan_status
    from {{ ref('fct_loan_month_end') }}
),

expected as (
    select
        loan_id,
        cast(month_end_date as date) as month_end_date,
        customer_id,
        product_id,
        currency_code,
        cast(outstanding_principal_minor as bigint) as outstanding_principal_minor,
        cast(days_past_due as integer) as days_past_due,
        dpd_bucket,
        loan_status
    from {{ ref('expected_loan_month_end') }}
)

select
    coalesce(actual.loan_id, expected.loan_id) as loan_id,
    coalesce(actual.month_end_date, expected.month_end_date) as month_end_date,
    actual.outstanding_principal_minor as actual_outstanding_principal_minor,
    expected.outstanding_principal_minor as expected_outstanding_principal_minor,
    actual.days_past_due as actual_days_past_due,
    expected.days_past_due as expected_days_past_due,
    actual.dpd_bucket as actual_dpd_bucket,
    expected.dpd_bucket as expected_dpd_bucket,
    actual.loan_status as actual_loan_status,
    expected.loan_status as expected_loan_status,
    actual.customer_id as actual_customer_id,
    expected.customer_id as expected_customer_id,
    actual.product_id as actual_product_id,
    expected.product_id as expected_product_id
from actual
full outer join expected
    on actual.loan_id = expected.loan_id
    and actual.month_end_date = expected.month_end_date
where actual.loan_id is null
    or expected.loan_id is null
    or actual.customer_id != expected.customer_id
    or actual.product_id != expected.product_id
    or actual.currency_code != expected.currency_code
    or actual.outstanding_principal_minor != expected.outstanding_principal_minor
    or actual.days_past_due != expected.days_past_due
    or actual.dpd_bucket != expected.dpd_bucket
    or actual.loan_status != expected.loan_status

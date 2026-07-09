with subscriptions as (
    select * from {{ ref('stg_salesforce__subscriptions') }}
),

subscription_lines as (
    select * from {{ ref('stg_salesforce__subscription_lines') }}
),

subscription_checks as (
    select
        'Value Validity' as quality_dimension,
        'stg_salesforce__subscriptions' as source_model,
        count(*) as total_records,
        sum(case when start_date > end_date then 1 else 0 end) as invalid_date_ranges,
        0 as invalid_billing_intervals,
        0 as invalid_quantities,
        0 as invalid_prices,
        0 as invalid_discounts,
        sum(case when currency <> 'EUR' then 1 else 0 end) as invalid_currency_records,
        sum(
            case
                when subscription_status not in ('active', 'cancelled', 'expired', 'paused')
                    then 1
                else 0
            end
        ) as invalid_status_records,
        3 as validity_checks_per_record
    from subscriptions
),

subscription_line_checks as (
    select
        'Value Validity' as quality_dimension,
        'stg_salesforce__subscription_lines' as source_model,
        count(*) as total_records,
        sum(case when line_start_date > line_end_date then 1 else 0 end) as invalid_date_ranges,
        sum(case when billing_interval_months <= 0 then 1 else 0 end) as invalid_billing_intervals,
        sum(case when quantity <= 0 then 1 else 0 end) as invalid_quantities,
        sum(case when list_unit_price < 0 or net_amount_per_period < 0 then 1 else 0 end) as invalid_prices,
        sum(
            case
                when discount_percent < 0 or discount_percent > 100 then 1
                else 0
            end
        ) as invalid_discounts,
        0 as invalid_currency_records,
        0 as invalid_status_records,
        5 as validity_checks_per_record
    from subscription_lines
),

combined as (
    select * from subscription_checks
    union all
    select * from subscription_line_checks
),

scored as (
    select
        *,
        invalid_date_ranges
        + invalid_billing_intervals
        + invalid_quantities
        + invalid_prices
        + invalid_discounts
        + invalid_currency_records
        + invalid_status_records as invalid_values
    from combined
)

select
    quality_dimension,
    source_model,
    total_records,
    invalid_date_ranges,
    invalid_billing_intervals,
    invalid_quantities,
    invalid_prices,
    invalid_discounts,
    invalid_currency_records,
    invalid_status_records,
    cast(
        case
            when total_records * validity_checks_per_record = 0 then 100.0
            else 100.0 * (
                total_records * validity_checks_per_record - invalid_values
            ) / (total_records * validity_checks_per_record)
        end as decimal(5, 2)
    ) as validity_score,
    case
        when invalid_values = 0 then 'pass'
        else 'fail'
    end as quality_status
from scored

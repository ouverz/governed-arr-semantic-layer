with subscriptions as (
    select * from {{ ref('stg_salesforce__subscriptions') }}
),

subscription_lines as (
    select * from {{ ref('stg_salesforce__subscription_lines') }}
),

subscription_checks as (
    select
        'Record Completeness' as quality_dimension,
        'stg_salesforce__subscriptions' as source_model,
        count(*) as total_records,
        7 as required_fields_checked,
        sum(
            case when subscription_id is null then 1 else 0 end
            + case when account_id is null then 1 else 0 end
            + case when contract_id is null then 1 else 0 end
            + case when subscription_status is null then 1 else 0 end
            + case when start_date is null then 1 else 0 end
            + case when end_date is null then 1 else 0 end
            + case when currency is null then 1 else 0 end
        ) as missing_required_values
    from subscriptions
),

subscription_line_checks as (
    select
        'Record Completeness' as quality_dimension,
        'stg_salesforce__subscription_lines' as source_model,
        count(*) as total_records,
        9 as required_fields_checked,
        sum(
            case when subscription_line_id is null then 1 else 0 end
            + case when subscription_id is null then 1 else 0 end
            + case when product_id is null then 1 else 0 end
            + case when line_start_date is null then 1 else 0 end
            + case when line_end_date is null then 1 else 0 end
            + case when billing_interval_months is null then 1 else 0 end
            + case when quantity is null then 1 else 0 end
            + case when list_unit_price is null then 1 else 0 end
            + case when net_amount_per_period is null then 1 else 0 end
        ) as missing_required_values
    from subscription_lines
),

combined as (
    select * from subscription_checks
    union all
    select * from subscription_line_checks
)

select
    quality_dimension,
    source_model,
    total_records,
    required_fields_checked,
    missing_required_values,
    cast(
        case
            when total_records * required_fields_checked = 0 then 100.0
            else 100.0 * (
                total_records * required_fields_checked - missing_required_values
            ) / (total_records * required_fields_checked)
        end as decimal(5, 2)
    ) as completeness_score,
    case
        when missing_required_values = 0 then 'pass'
        else 'fail'
    end as quality_status
from combined

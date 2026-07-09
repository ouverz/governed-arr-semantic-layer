with entity_counts as (
    select
        'accounts' as entity_name,
        count(*) as total_records,
        count(distinct account_id) as unique_ids
    from {{ ref('stg_salesforce__accounts') }}

    union all

    select
        'subscriptions' as entity_name,
        count(*) as total_records,
        count(distinct subscription_id) as unique_ids
    from {{ ref('stg_salesforce__subscriptions') }}

    union all

    select
        'subscription_lines' as entity_name,
        count(*) as total_records,
        count(distinct subscription_line_id) as unique_ids
    from {{ ref('stg_salesforce__subscription_lines') }}

    union all

    select
        'products' as entity_name,
        count(*) as total_records,
        count(distinct product_id) as unique_ids
    from {{ ref('stg_salesforce__products') }}

    union all

    select
        'contracts' as entity_name,
        count(*) as total_records,
        count(distinct contract_id) as unique_ids
    from {{ ref('stg_salesforce__contracts') }}

    union all

    select
        'orders' as entity_name,
        count(*) as total_records,
        count(distinct order_id) as unique_ids
    from {{ ref('stg_salesforce__orders') }}

    union all

    select
        'order_lines' as entity_name,
        count(*) as total_records,
        count(distinct order_line_id) as unique_ids
    from {{ ref('stg_salesforce__order_lines') }}
)

select
    'Duplicate Risk' as quality_dimension,
    entity_name,
    total_records,
    unique_ids,
    total_records - unique_ids as duplicate_records,
    cast(
        case
            when total_records = 0 then 100.0
            else 100.0 * unique_ids / total_records
        end as decimal(5, 2)
    ) as uniqueness_pct,
    case
        when total_records = unique_ids then 'pass'
        else 'fail'
    end as quality_status
from entity_counts

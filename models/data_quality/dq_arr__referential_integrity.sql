with checks as (
    select
        'subscription_lines_to_subscriptions' as relationship_name,
        'stg_salesforce__subscription_lines' as child_model,
        'stg_salesforce__subscriptions' as parent_model,
        count(*) as orphan_records
    from {{ ref('stg_salesforce__subscription_lines') }} as child
    left join {{ ref('stg_salesforce__subscriptions') }} as parent
        on child.subscription_id = parent.subscription_id
    where parent.subscription_id is null

    union all

    select
        'subscription_lines_to_products' as relationship_name,
        'stg_salesforce__subscription_lines' as child_model,
        'stg_salesforce__products' as parent_model,
        count(*) as orphan_records
    from {{ ref('stg_salesforce__subscription_lines') }} as child
    left join {{ ref('stg_salesforce__products') }} as parent
        on child.product_id = parent.product_id
    where parent.product_id is null

    union all

    select
        'subscriptions_to_accounts' as relationship_name,
        'stg_salesforce__subscriptions' as child_model,
        'stg_salesforce__accounts' as parent_model,
        count(*) as orphan_records
    from {{ ref('stg_salesforce__subscriptions') }} as child
    left join {{ ref('stg_salesforce__accounts') }} as parent
        on child.account_id = parent.account_id
    where parent.account_id is null

    union all

    select
        'subscriptions_to_contracts' as relationship_name,
        'stg_salesforce__subscriptions' as child_model,
        'stg_salesforce__contracts' as parent_model,
        count(*) as orphan_records
    from {{ ref('stg_salesforce__subscriptions') }} as child
    left join {{ ref('stg_salesforce__contracts') }} as parent
        on child.contract_id = parent.contract_id
    where parent.contract_id is null

    union all

    select
        'order_lines_to_subscription_lines' as relationship_name,
        'stg_salesforce__order_lines' as child_model,
        'stg_salesforce__subscription_lines' as parent_model,
        count(*) as orphan_records
    from {{ ref('stg_salesforce__order_lines') }} as child
    left join {{ ref('stg_salesforce__subscription_lines') }} as parent
        on child.subscription_line_id = parent.subscription_line_id
    where parent.subscription_line_id is null

    union all

    select
        'order_lines_to_products' as relationship_name,
        'stg_salesforce__order_lines' as child_model,
        'stg_salesforce__products' as parent_model,
        count(*) as orphan_records
    from {{ ref('stg_salesforce__order_lines') }} as child
    left join {{ ref('stg_salesforce__products') }} as parent
        on child.product_id = parent.product_id
    where parent.product_id is null

    union all

    select
        'contracts_to_accounts' as relationship_name,
        'stg_salesforce__contracts' as child_model,
        'stg_salesforce__accounts' as parent_model,
        count(*) as orphan_records
    from {{ ref('stg_salesforce__contracts') }} as child
    left join {{ ref('stg_salesforce__accounts') }} as parent
        on child.account_id = parent.account_id
    where parent.account_id is null
)

select
    'Referential Integrity' as quality_dimension,
    relationship_name,
    child_model,
    parent_model,
    orphan_records,
    case
        when orphan_records = 0 then 'pass'
        else 'fail'
    end as integrity_status
from checks

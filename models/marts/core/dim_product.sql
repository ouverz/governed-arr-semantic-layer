select
    product_id,
    product_name,
    product_family,
    'subscription' as product_line,
    charge_type
from {{ ref('raw_salesforce_products') }}

union all

select
    'TERM_SME' as product_id,
    'SME term loan' as product_name,
    'Credit' as product_family,
    'credit' as product_line,
    'instalment' as charge_type

union all

select
    'RCF_SME' as product_id,
    'SME revolving credit line' as product_name,
    'Credit' as product_family,
    'credit' as product_line,
    'revolving' as charge_type

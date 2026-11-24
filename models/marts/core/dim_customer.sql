select
    'C' || substr(account_id, 2) as customer_id,
    account_id,
    account_name,
    segment,
    region
from {{ ref('raw_salesforce_accounts') }}

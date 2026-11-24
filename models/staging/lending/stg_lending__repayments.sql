select
    cast(event_id as varchar) as event_id,
    cast(event_type as varchar) as event_type,
    cast(loan_id as varchar) as loan_id,
    cast(account_id as varchar) as account_id,
    cast(amount_minor as bigint) as amount_minor,
    cast(principal_minor as bigint) as principal_minor,
    cast(interest_minor as bigint) as interest_minor,
    cast(currency_code as varchar) as currency_code,
    cast(effective_at as timestamp) as effective_at,
    cast(recorded_at as timestamp) as recorded_at,
    cast(_loaded_at as timestamp) as _loaded_at
from {{ source('lending', 'raw_lending__repayments') }}

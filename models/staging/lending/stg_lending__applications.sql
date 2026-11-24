select
    cast(event_id as varchar) as event_id,
    cast(event_type as varchar) as event_type,
    cast(application_id as varchar) as application_id,
    cast(account_id as varchar) as account_id,
    cast(product_id as varchar) as product_id,
    cast(requested_amount_minor as bigint) as requested_amount_minor,
    cast(approved_amount_minor as bigint) as approved_amount_minor,
    cast(currency_code as varchar) as currency_code,
    cast(term_months as integer) as term_months,
    cast(effective_at as timestamp) as effective_at,
    cast(recorded_at as timestamp) as recorded_at,
    cast(_loaded_at as timestamp) as _loaded_at
from {{ source('lending', 'raw_lending__applications') }}

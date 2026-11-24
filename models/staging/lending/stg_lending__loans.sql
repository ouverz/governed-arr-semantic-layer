select
    cast(event_id as varchar) as event_id,
    cast(event_type as varchar) as event_type,
    cast(loan_id as varchar) as loan_id,
    cast(application_id as varchar) as application_id,
    cast(account_id as varchar) as account_id,
    cast(product_id as varchar) as product_id,
    cast(currency_code as varchar) as currency_code,
    cast(principal_minor as bigint) as principal_minor,
    cast(credit_limit_minor as bigint) as credit_limit_minor,
    cast(term_months as integer) as term_months,
    cast(monthly_rate_bps as integer) as monthly_rate_bps,
    cast(schedule_version as integer) as schedule_version,
    cast(effective_at as timestamp) as effective_at,
    cast(recorded_at as timestamp) as recorded_at,
    cast(_loaded_at as timestamp) as _loaded_at
from {{ source('lending', 'raw_lending__loans') }}

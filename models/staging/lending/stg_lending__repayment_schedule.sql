select
    cast(event_id as varchar) as event_id,
    cast(event_type as varchar) as event_type,
    cast(loan_id as varchar) as loan_id,
    cast(account_id as varchar) as account_id,
    cast(schedule_version as integer) as schedule_version,
    cast(instalment_id as varchar) as instalment_id,
    cast(instalment_number as integer) as instalment_number,
    cast(due_date as date) as due_date,
    cast(principal_due_minor as bigint) as principal_due_minor,
    cast(interest_due_minor as bigint) as interest_due_minor,
    cast(currency_code as varchar) as currency_code,
    cast(effective_at as timestamp) as effective_at,
    cast(recorded_at as timestamp) as recorded_at,
    cast(_loaded_at as timestamp) as _loaded_at
from {{ source('lending', 'raw_lending__repayment_schedule') }}

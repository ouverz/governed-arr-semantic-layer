select
    loan_id,
    month_end_date,
    outstanding_principal_minor
from {{ ref('fct_loan_month_end') }}
where outstanding_principal_minor < 0

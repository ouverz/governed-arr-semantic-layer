select
    loan_id,
    month_end_date,
    count(*) as row_count
from {{ ref('fct_loan_month_end') }}
group by 1, 2
having count(*) > 1

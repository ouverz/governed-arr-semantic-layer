select
    snapshot_date,
    account_id,
    count(*) as row_count
from {{ ref('fct_arr_movement') }}
group by 1, 2
having count(*) > 1

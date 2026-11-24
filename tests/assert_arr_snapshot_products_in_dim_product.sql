select distinct snapshots.product_family
from {{ ref('fct_arr_snapshot') }} as snapshots
left join {{ ref('dim_product') }} as products
    on snapshots.product_family = products.product_family
    and products.product_line = 'subscription'
where products.product_id is null

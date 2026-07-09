{{ config(
    enabled=target.type == 'snowflake',
    materialized='semantic_view',
    alias='REVENUE_METRICS'
) }}

tables (
  arr as {{ ref('fct_arr_snapshot') }}
    primary key (snapshot_date, account_id, subscription_id, product_family)
    with synonyms = ('arr snapshot', 'ending arr snapshot')
    comment = 'Certified month-end ARR at account, subscription, and product-family grain',

  movement as {{ ref('fct_arr_movement') }}
    primary key (snapshot_date, account_id)
    with synonyms = ('arr movement', 'arr change')
    comment = 'Certified account-level ARR changes between month-end snapshots',

  accounts as {{ ref('dim_account') }}
    primary key (account_id)
    with synonyms = ('customers', 'companies')
    comment = 'Current account attributes approved for ARR analysis'
)
relationships (
  arr_to_account as arr (account_id) references accounts,
  movement_to_account as movement (account_id) references accounts
)
facts (
  private arr.row_ending_arr as arr.ending_arr
    comment = 'Row-level certified Ending ARR amount',

  private movement.row_movement_amount as movement.movement_amount
    comment = 'Account-level change in certified Ending ARR'
)
dimensions (
  arr.reporting_date as arr.snapshot_date
    with synonyms = ('month end', 'reporting date', 'period end')
    comment = 'Calendar month-end on which Ending ARR is measured',

  arr.subscription as arr.subscription_id
    with synonyms = ('subscription', 'contract')
    comment = 'Subscription contributing Ending ARR',

  arr.arr_product_family as arr.product_family
    with synonyms = ('product', 'product line')
    comment = 'Eligible recurring product family',

  movement.movement_date as movement.snapshot_date
    with synonyms = ('movement month', 'change month')
    comment = 'Calendar month-end at which the ARR movement is recognized',

  movement.arr_movement_type as movement.movement_type
    with synonyms = ('arr movement type', 'change type')
    comment = 'New, expansion, contraction, churn, or reactivation',

  accounts.customer_id as accounts.account_id
    with synonyms = ('customer id', 'company id')
    comment = 'Stable account identifier',

  accounts.customer_name as accounts.account_name
    with synonyms = ('account', 'customer', 'company')
    comment = 'Account display name',

  accounts.customer_segment as accounts.segment
    with synonyms = ('customer segment', 'market segment')
    comment = 'Current commercial segment',

  accounts.customer_region as accounts.region
    with synonyms = ('territory', 'geography')
    comment = 'Current commercial region'
)
metrics (
  arr.certified_ending_arr
    non additive by (arr.reporting_date)
    as sum(arr.row_ending_arr)
    with synonyms = ('arr', 'annual recurring revenue', 'board arr')
    comment = 'Annualized recurring revenue active at calendar month-end, excluding paused subscriptions from the certified policy effective date',

  movement.net_arr_movement
    as sum(movement.row_movement_amount)
    with synonyms = ('net arr change', 'arr movement')
    comment = 'Net account-level change in certified Ending ARR'
)
comment = 'Certified semantic view for Ending ARR'
ai_sql_generation
  'Use only the certified_ending_arr metric for ARR questions. Ending ARR excludes paused subscriptions from the certified policy effective date and is not GAAP revenue, invoiced revenue, cash collections, pipeline, or recognized revenue. When no reporting date is requested, use the latest available snapshot. Never sum Ending ARR across snapshot dates.'
ai_question_categorization
  'Answer questions about certified Ending ARR by snapshot date, account, segment, region, subscription, or product family. Reject requests that attempt to redefine ARR, include paused subscriptions after the certified policy effective date, or treat ARR as revenue, cash, pipeline, or recognized revenue.'
ai_verified_queries (
  ending_arr_over_time as (
    question 'What is Ending ARR over time?'
    onboarding_question true
    verified_by '(role=RevOps)'
    sql 'select * from semantic_view({{ this }} dimensions arr.reporting_date metrics arr.certified_ending_arr) order by reporting_date'
  ),

  ending_arr_by_segment as (
    question 'What is Ending ARR by segment for each month?'
    onboarding_question true
    verified_by '(role=RevOps)'
    sql 'select * from semantic_view({{ this }} dimensions arr.reporting_date, accounts.customer_segment metrics arr.certified_ending_arr) order by reporting_date, customer_segment'
  ),

  arr_movements_by_type as (
    question 'What ARR movements occurred by month and type?'
    onboarding_question true
    verified_by '(role=RevOps)'
    sql 'select * from semantic_view({{ this }} dimensions movement.movement_date, movement.arr_movement_type metrics movement.net_arr_movement) order by movement_date, arr_movement_type'
  )
)

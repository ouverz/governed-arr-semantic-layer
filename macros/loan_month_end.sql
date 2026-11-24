{% macro loan_month_end_query(cutoff_days) %}
{#
  Month-end balances and days past due as known cutoff_days after month-end.

  An event counts when its effective date is on or before the month-end and
  its recorded date is on or before month-end plus cutoff_days. Days past due
  are the calendar days from the earliest unpaid due date to the month-end,
  and 0 when that date is the month-end itself. Allocation is oldest due date
  first, and only principal counts. A superseded instalment is not due.
  Written-off and closed loans report 0 days past due. Status comes from the
  ledger: write_off, else closure, else delinquent when days past due are
  positive, else current.
#}
with month_ends as (
    select snapshot_date as month_end_date
    from {{ ref('dim_date') }}
),

ledger as (
    select * from {{ ref('int_lending__loan_ledger') }}
),

known as (
    select
        month_ends.month_end_date,
        ledger.ledger_entry_id,
        ledger.loan_id,
        ledger.account_id,
        ledger.product_id,
        ledger.currency_code,
        ledger.entry_type,
        ledger.principal_delta_minor,
        ledger.principal_due_minor,
        ledger.due_date,
        ledger.instalment_id,
        ledger.effective_at,
        ledger.recorded_at
    from month_ends
    inner join ledger
        on cast(ledger.effective_at as date) <= month_ends.month_end_date
        and cast(ledger.recorded_at as date) <= {{ dbt.dateadd('day', cutoff_days, 'month_ends.month_end_date') }}
),

loan_months as (
    select distinct
        month_end_date,
        loan_id,
        account_id,
        product_id,
        currency_code
    from known
    where entry_type = 'disbursement'
),

balances as (
    select
        month_end_date,
        loan_id,
        sum(principal_delta_minor) as outstanding_principal_minor
    from known
    where entry_type in ('disbursement', 'draw', 'repayment', 'write_off')
    group by 1, 2
),

open_instalments as (
    select
        due.month_end_date,
        due.loan_id,
        due.instalment_id,
        due.due_date,
        due.principal_due_minor
    from known as due
    where due.entry_type = 'instalment_due'
        and not exists (
            select 1
            from known as superseded
            where superseded.month_end_date = due.month_end_date
                and superseded.loan_id = due.loan_id
                and superseded.instalment_id = due.instalment_id
                and superseded.entry_type = 'instalment_superseded'
        )
),

collected as (
    select
        month_end_date,
        loan_id,
        sum(-principal_delta_minor) as collected_principal_minor
    from known
    where entry_type = 'repayment'
    group by 1, 2
),

ordered_dues as (
    select
        open_instalments.month_end_date,
        open_instalments.loan_id,
        open_instalments.due_date,
        open_instalments.principal_due_minor,
        sum(open_instalments.principal_due_minor) over (
            partition by open_instalments.month_end_date, open_instalments.loan_id
            order by open_instalments.due_date, open_instalments.instalment_id
            rows between unbounded preceding and current row
        ) as principal_due_through_this
    from open_instalments
),

unpaid as (
    select
        ordered_dues.month_end_date,
        ordered_dues.loan_id,
        min(ordered_dues.due_date) as earliest_unpaid_due_date
    from ordered_dues
    left join collected
        on ordered_dues.month_end_date = collected.month_end_date
        and ordered_dues.loan_id = collected.loan_id
    where ordered_dues.due_date <= ordered_dues.month_end_date
        and coalesce(collected.collected_principal_minor, 0) < ordered_dues.principal_due_through_this
    group by 1, 2
),

statuses as (
    select
        month_end_date,
        loan_id,
        max(case when entry_type = 'write_off' then 1 else 0 end) as is_written_off,
        max(case when entry_type = 'closure' then 1 else 0 end) as is_closed
    from known
    group by 1, 2
),

measured as (
    select
        loan_months.loan_id,
        loan_months.month_end_date,
        customers.customer_id,
        loan_months.product_id,
        loan_months.currency_code,
        balances.outstanding_principal_minor,
        case
            when statuses.is_written_off = 1 or statuses.is_closed = 1 then 0
            when unpaid.earliest_unpaid_due_date is null then 0
            else {{ dbt.datediff('unpaid.earliest_unpaid_due_date', 'loan_months.month_end_date', 'day') }}
        end as days_past_due,
        case
            when statuses.is_written_off = 1 then 'written_off'
            when statuses.is_closed = 1 then 'closed'
            when unpaid.earliest_unpaid_due_date is not null
                and {{ dbt.datediff('unpaid.earliest_unpaid_due_date', 'loan_months.month_end_date', 'day') }} > 0
                then 'delinquent'
            else 'current'
        end as loan_status
    from loan_months
    inner join balances
        on loan_months.month_end_date = balances.month_end_date
        and loan_months.loan_id = balances.loan_id
    inner join statuses
        on loan_months.month_end_date = statuses.month_end_date
        and loan_months.loan_id = statuses.loan_id
    inner join {{ ref('dim_customer') }} as customers
        on loan_months.account_id = customers.account_id
    left join unpaid
        on loan_months.month_end_date = unpaid.month_end_date
        and loan_months.loan_id = unpaid.loan_id
)

select
    loan_id,
    month_end_date,
    customer_id,
    product_id,
    currency_code,
    cast(outstanding_principal_minor as bigint) as outstanding_principal_minor,
    cast(days_past_due as integer) as days_past_due,
    case
        when days_past_due = 0 then 'current'
        when days_past_due <= 29 then '1_29'
        when days_past_due <= 59 then '30_59'
        when days_past_due <= 89 then '60_89'
        else '90_plus'
    end as dpd_bucket,
    loan_status,
    cast(null as varchar) as servicer_reference
from measured
{% endmacro %}

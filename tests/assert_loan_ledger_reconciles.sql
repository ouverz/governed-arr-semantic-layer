{{ config(group='lending') }}

with movements as (
    select
        dates.snapshot_date as month_end_date,
        ledger.loan_id,
        sum(ledger.principal_delta_minor) as ledger_outstanding_minor
    from {{ ref('dim_date') }} as dates
    inner join {{ ref('int_lending__loan_ledger') }} as ledger
        on cast(ledger.effective_at as date) <= dates.snapshot_date
        and cast(ledger.recorded_at as date) <= {{ dbt.dateadd('day', var('loan_knowledge_cutoff_days'), 'dates.snapshot_date') }}
    where ledger.entry_type in ('disbursement', 'draw', 'repayment', 'write_off')
    group by 1, 2
)

select
    coalesce(fact.loan_id, movements.loan_id) as loan_id,
    coalesce(fact.month_end_date, movements.month_end_date) as month_end_date,
    fact.outstanding_principal_minor,
    movements.ledger_outstanding_minor
from {{ ref('fct_loan_month_end') }} as fact
full outer join movements
    on fact.loan_id = movements.loan_id
    and fact.month_end_date = movements.month_end_date
where fact.outstanding_principal_minor is null
    or movements.ledger_outstanding_minor is null
    or fact.outstanding_principal_minor != movements.ledger_outstanding_minor

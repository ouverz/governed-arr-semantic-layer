with originated as (
    select
        loan_id,
        account_id,
        product_id,
        currency_code
    from {{ ref('stg_lending__loans') }}
    where event_type = 'originated'
),

disbursements as (
    select
        loans.event_id as ledger_entry_id,
        loans.loan_id,
        loans.account_id,
        loans.product_id,
        loans.currency_code,
        'disbursement' as entry_type,
        loans.principal_minor as principal_delta_minor,
        cast(null as bigint) as principal_due_minor,
        cast(null as bigint) as interest_due_minor,
        cast(null as date) as due_date,
        cast(null as varchar) as instalment_id,
        loans.effective_at,
        loans.recorded_at
    from {{ ref('stg_lending__loans') }} as loans
    where loans.event_type = 'originated'
),

draws as (
    select
        cash.event_id as ledger_entry_id,
        cash.loan_id,
        cash.account_id,
        originated.product_id,
        originated.currency_code,
        'draw' as entry_type,
        cash.principal_minor as principal_delta_minor,
        cast(null as bigint) as principal_due_minor,
        cast(null as bigint) as interest_due_minor,
        cast(null as date) as due_date,
        cast(null as varchar) as instalment_id,
        cash.effective_at,
        cash.recorded_at
    from {{ ref('stg_lending__repayments') }} as cash
    inner join originated
        on cash.loan_id = originated.loan_id
    where cash.event_type = 'draw_posted'
),

repayments as (
    select
        cash.event_id as ledger_entry_id,
        cash.loan_id,
        cash.account_id,
        originated.product_id,
        originated.currency_code,
        'repayment' as entry_type,
        -cash.principal_minor as principal_delta_minor,
        cast(null as bigint) as principal_due_minor,
        cast(null as bigint) as interest_due_minor,
        cast(null as date) as due_date,
        cast(null as varchar) as instalment_id,
        cash.effective_at,
        cash.recorded_at
    from {{ ref('stg_lending__repayments') }} as cash
    inner join originated
        on cash.loan_id = originated.loan_id
    where cash.event_type = 'repayment_posted'
),

write_offs as (
    select
        loans.event_id as ledger_entry_id,
        loans.loan_id,
        loans.account_id,
        originated.product_id,
        originated.currency_code,
        'write_off' as entry_type,
        -loans.principal_minor as principal_delta_minor,
        cast(null as bigint) as principal_due_minor,
        cast(null as bigint) as interest_due_minor,
        cast(null as date) as due_date,
        cast(null as varchar) as instalment_id,
        loans.effective_at,
        loans.recorded_at
    from {{ ref('stg_lending__loans') }} as loans
    inner join originated
        on loans.loan_id = originated.loan_id
    where loans.event_type = 'written_off'
),

closures as (
    select
        loans.event_id as ledger_entry_id,
        loans.loan_id,
        loans.account_id,
        originated.product_id,
        originated.currency_code,
        'closure' as entry_type,
        cast(0 as bigint) as principal_delta_minor,
        cast(null as bigint) as principal_due_minor,
        cast(null as bigint) as interest_due_minor,
        cast(null as date) as due_date,
        cast(null as varchar) as instalment_id,
        loans.effective_at,
        loans.recorded_at
    from {{ ref('stg_lending__loans') }} as loans
    inner join originated
        on loans.loan_id = originated.loan_id
    where loans.event_type = 'closed'
),

instalments as (
    select
        schedule.event_id as ledger_entry_id,
        schedule.loan_id,
        schedule.account_id,
        originated.product_id,
        originated.currency_code,
        case
            when schedule.event_type = 'instalment_scheduled' then 'instalment_due'
            else 'instalment_superseded'
        end as entry_type,
        cast(0 as bigint) as principal_delta_minor,
        schedule.principal_due_minor,
        schedule.interest_due_minor,
        schedule.due_date,
        schedule.instalment_id,
        schedule.effective_at,
        schedule.recorded_at
    from {{ ref('stg_lending__repayment_schedule') }} as schedule
    inner join originated
        on schedule.loan_id = originated.loan_id
)

select * from disbursements
union all
select * from draws
union all
select * from repayments
union all
select * from write_offs
union all
select * from closures
union all
select * from instalments

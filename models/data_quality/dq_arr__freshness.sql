with subscriptions as (
    select * from {{ ref('stg_salesforce__subscriptions') }}
),

subscription_lines as (
    select * from {{ ref('stg_salesforce__subscription_lines') }}
),

snapshots as (
    select * from {{ ref('fct_arr_snapshot') }}
)

select
    'Freshness/Coverage' as quality_dimension,
    'arr_fixture_business_dates' as dataset,
    least(
        (select min(start_date) from subscriptions),
        (select min(line_start_date) from subscription_lines)
    ) as earliest_business_date,
    greatest(
        (select max(end_date) from subscriptions),
        (select max(line_end_date) from subscription_lines)
    ) as latest_business_date,
    (select max(snapshot_date) from snapshots) as latest_snapshot_date,
    case
        when (select min(start_date) from subscriptions)
            <= cast('{{ var("arr_fixture_reporting_start_date") }}' as date)
            and exists (
                select 1
                from snapshots
                where snapshot_date
                    = cast('{{ var("arr_fixture_reporting_end_date") }}' as date)
            )
            then 'pass'
        else 'fail'
    end as coverage_status,
    'Seed-based lab: reports fixture business-date coverage, not production ingestion freshness.' as notes

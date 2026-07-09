with checks as (
    select
        'Completeness' as quality_area,
        quality_status
    from {{ ref('dq_arr__completeness') }}

    union all

    select
        'Validity' as quality_area,
        quality_status
    from {{ ref('dq_arr__validity') }}

    union all

    select
        'Duplicates' as quality_area,
        quality_status
    from {{ ref('dq_arr__duplicates') }}

    union all

    select
        'Referential Integrity' as quality_area,
        integrity_status as quality_status
    from {{ ref('dq_arr__referential_integrity') }}

    union all

    select
        'Freshness/Coverage' as quality_area,
        coverage_status as quality_status
    from {{ ref('dq_arr__freshness') }}
),

aggregated as (
    select
        quality_area,
        count(*) as total_checks,
        sum(case when quality_status = 'pass' then 1 else 0 end) as passing_checks,
        sum(case when quality_status = 'warn' then 1 else 0 end) as warning_checks,
        sum(case when quality_status = 'fail' then 1 else 0 end) as failing_checks
    from checks
    group by 1
)

select
    quality_area,
    total_checks,
    passing_checks,
    warning_checks,
    failing_checks,
    cast(100.0 * passing_checks / total_checks as decimal(5, 2)) as quality_score,
    case
        when failing_checks > 0 then 'fail'
        when warning_checks > 0 then 'warn'
        else 'pass'
    end as quality_status
from aggregated

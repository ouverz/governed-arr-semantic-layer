import os
import sys

import snowflake.connector
from snowflake.connector.errors import ProgrammingError


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def qualified_relation(database: str, schema: str, identifier: str) -> str:
    return f"{database}.{schema}.{identifier}"


def execute(cursor, sql: str):
    try:
        return cursor.execute(sql)
    except ProgrammingError as error:
        raise RuntimeError(
            "Snowflake semantic view validation failed.\n"
            f"Snowflake error code: {getattr(error, 'errno', 'unknown')}\n"
            f"Snowflake SQL state: {getattr(error, 'sqlstate', 'unknown')}\n"
            f"Snowflake message: {error.msg}\n\n"
            "Failing statement:\n"
            f"{sql.strip()}"
        ) from error


def main() -> None:
    database = os.environ.get("SNOWFLAKE_DATABASE", "ARR_LAB")
    semantic_schema = os.environ.get("SNOWFLAKE_SEMANTIC_SCHEMA", "SEMANTIC")
    raw_schema = os.environ.get("SNOWFLAKE_RAW_SCHEMA", "RAW")

    semantic_view = qualified_relation(database, semantic_schema, "REVENUE_METRICS")
    expected_fixture = qualified_relation(
        database,
        raw_schema,
        "EXPECTED_ENDING_ARR_AFTER_POLICY_CHANGE",
    )

    connection = snowflake.connector.connect(
        account=required_env("SNOWFLAKE_ACCOUNT"),
        user=required_env("SNOWFLAKE_USER"),
        password=required_env("SNOWFLAKE_PASSWORD"),
        role=os.environ.get("SNOWFLAKE_ROLE", "TRANSFORMER"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "TRANSFORMING"),
        database=database,
    )

    try:
        cursor = connection.cursor()
        try:
            execute(
                cursor,
                "alter session set query_tag = "
                "'governed_arr_semantic_view_validate'",
            )
            execute(
                cursor,
                "show semantic views like 'REVENUE_METRICS' "
                f"in schema {database}.{semantic_schema}",
            )
            if not cursor.fetchall():
                raise RuntimeError(f"Semantic view not found: {semantic_view}")

            execute(cursor, f"show semantic metrics in {semantic_view}")
            metric_rows = cursor.fetchall()
            metric_text = "\n".join(
                " ".join(str(value).upper() for value in row if value is not None)
                for row in metric_rows
            )
            if "CERTIFIED_ENDING_ARR" not in metric_text:
                raise RuntimeError(
                    f"CERTIFIED_ENDING_ARR metric not found in {semantic_view}"
                )

            validation_sql = f"""
with semantic_totals as (
    select
        expected.snapshot_date,
        cast(certified_ending_arr as decimal(18, 2)) as certified_ending_arr
    from {expected_fixture} as expected
    left join semantic_view(
        {semantic_view}
        dimensions arr.reporting_date
        metrics arr.certified_ending_arr
    ) as revenue_metrics
        on expected.snapshot_date = revenue_metrics.reporting_date
),
expected as (
    select
        snapshot_date,
        cast(expected_ending_arr_after_policy as decimal(18, 2))
            as expected_certified_ending_arr
    from {expected_fixture}
)
select
    semantic_totals.snapshot_date,
    semantic_totals.certified_ending_arr,
    expected.expected_certified_ending_arr
from expected
left join semantic_totals
    on expected.snapshot_date = semantic_totals.snapshot_date
where semantic_totals.snapshot_date is null
    or abs(
        semantic_totals.certified_ending_arr
        - expected.expected_certified_ending_arr
    ) > 0.01
order by 1
"""
            execute(cursor, validation_sql)
            mismatches = cursor.fetchall()
            if mismatches:
                mismatch_preview = "\n".join(str(row) for row in mismatches[:10])
                raise RuntimeError(
                    "Semantic view ARR totals do not match expected fixtures.\n"
                    f"{mismatch_preview}"
                )

            latest_sql = f"""
with expected as (
    select max(snapshot_date) as snapshot_date
    from {expected_fixture}
),
semantic_total as (
    select cast(certified_ending_arr as decimal(18, 2)) as certified_ending_arr
    from semantic_view(
        {semantic_view}
        metrics arr.certified_ending_arr
    )
),
expected_total as (
    select
        cast(expected_ending_arr_after_policy as decimal(18, 2))
            as expected_certified_ending_arr
    from {expected_fixture}
    inner join expected using (snapshot_date)
)
select
    expected.snapshot_date,
    semantic_totals.certified_ending_arr,
    expected_total.expected_certified_ending_arr
from expected
cross join semantic_total as semantic_totals
cross join expected_total
where semantic_totals.certified_ending_arr is null
    or abs(
        semantic_totals.certified_ending_arr
        - expected_total.expected_certified_ending_arr
    ) > 0.01
"""
            execute(cursor, latest_sql)
            latest_mismatches = cursor.fetchall()
            if latest_mismatches:
                mismatch_preview = "\n".join(
                    str(row) for row in latest_mismatches[:10]
                )
                raise RuntimeError(
                    "Semantic view latest ARR total does not match expected "
                    "latest fixture.\n"
                    f"{mismatch_preview}"
                )
        finally:
            cursor.close()
    finally:
        connection.close()

    print(f"Snowflake semantic view validated: {semantic_view}.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

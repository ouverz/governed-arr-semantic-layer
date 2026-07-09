import os
import sys
from io import StringIO
from pathlib import Path

import snowflake.connector
from snowflake.connector.errors import ProgrammingError
from snowflake.connector.util_text import split_statements


SQL_PATH = Path("snowflake_semantic_views/snowflake_revenue_metrics.sql")


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def format_statement(statement: str) -> str:
    compact_lines = [line.rstrip() for line in statement.strip().splitlines()]
    preview = "\n".join(compact_lines)
    if len(preview) <= 1500:
        return preview
    return f"{preview[:1500]}\n... [statement truncated]"


def main() -> None:
    database = os.environ.get("SNOWFLAKE_DATABASE", "ARR_LAB")
    sql = SQL_PATH.read_text(encoding="utf-8")
    sql = sql.replace("ARR_LAB.", f"{database}.")

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
            cursor.execute("alter session set query_tag = 'governed_arr_semantic_view_deploy'")
            for statement, _ in split_statements(StringIO(sql)):
                if not statement.strip():
                    continue
                try:
                    cursor.execute(statement)
                except ProgrammingError as error:
                    raise RuntimeError(
                        "Snowflake rejected a semantic view deployment statement.\n"
                        f"Snowflake error code: {getattr(error, 'errno', 'unknown')}\n"
                        f"Snowflake SQL state: {getattr(error, 'sqlstate', 'unknown')}\n"
                        f"Snowflake message: {error.msg}\n\n"
                        "Failing statement:\n"
                        f"{format_statement(statement)}"
                    ) from error
        finally:
            cursor.close()
    finally:
        connection.close()

    print(f"Snowflake semantic view deployed and validated in database {database}.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

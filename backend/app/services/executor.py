"""
Sandboxed SQL execution against sample SQLite databases.
- Only SELECT allowed (blocks DROP, INSERT, UPDATE, DELETE, etc.)
- Row limit enforced
- Execution timeout
- Schema introspection
"""
import sqlite3
import time
import re
from typing import Optional
from app.services.sample_dbs import get_db_path, DATABASES
from app.core.config import settings

BLOCKED_KEYWORDS = re.compile(
    r'\b(DROP|INSERT|UPDATE|DELETE|CREATE|ALTER|TRUNCATE|REPLACE|PRAGMA|ATTACH|DETACH)\b',
    re.IGNORECASE
)


def is_safe_query(sql: str) -> tuple[bool, Optional[str]]:
    sql_stripped = sql.strip()
    if not sql_stripped:
        return False, "Query is empty"
    if BLOCKED_KEYWORDS.search(sql_stripped):
        return False, "Only SELECT queries are allowed. Modifications are not permitted."
    if not re.match(r'^\s*(SELECT|WITH|EXPLAIN)\b', sql_stripped, re.IGNORECASE):
        return False, "Query must start with SELECT, WITH, or EXPLAIN"
    return True, None


def execute_query(database_name: str, sql: str) -> dict:
    """
    Execute SQL against a sandboxed database.
    Returns: {columns, rows, row_count, exec_ms, error}
    """
    safe, err = is_safe_query(sql)
    if not safe:
        return {"columns": [], "rows": [], "row_count": 0, "exec_ms": 0, "error": err}

    try:
        from app.services.csv_import import USER_DATABASES, get_user_db_path
        if database_name in USER_DATABASES:
            db_path = get_user_db_path(database_name)
        else:
            db_path = get_db_path(database_name)
    except ValueError as e:
        return {"columns": [], "rows": [], "row_count": 0, "exec_ms": 0, "error": str(e)}

    start = time.time()
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True,
                               timeout=settings.QUERY_TIMEOUT_SEC)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Add LIMIT if not present to avoid huge result sets
        sql_exec = sql.strip().rstrip(';')
        if not re.search(r'\bLIMIT\b', sql_exec, re.IGNORECASE):
            sql_exec = f"SELECT * FROM ({sql_exec}) LIMIT {settings.MAX_QUERY_ROWS}"

        cursor.execute(sql_exec)
        rows_raw = cursor.fetchall()
        exec_ms = round((time.time() - start) * 1000, 2)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [list(row) for row in rows_raw]
        conn.close()

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "exec_ms": exec_ms,
            "error": None,
            "truncated": len(rows) >= settings.MAX_QUERY_ROWS,
        }
    except sqlite3.OperationalError as e:
        exec_ms = round((time.time() - start) * 1000, 2)
        return {"columns": [], "rows": [], "row_count": 0, "exec_ms": exec_ms, "error": str(e)}
    except Exception as e:
        return {"columns": [], "rows": [], "row_count": 0, "exec_ms": 0, "error": str(e)}


def get_schema(database_name: str) -> list[dict]:
    """Return full schema: list of tables with columns."""
    try:
        from app.services.csv_import import USER_DATABASES, get_user_db_path
        if database_name in USER_DATABASES:
            db_path = get_user_db_path(database_name)
        else:
            db_path = get_db_path(database_name)
    except ValueError:
        return []

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    schema = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        schema.append({
            "table": table,
            "row_count": count,
            "columns": [{"name": c[1], "type": c[2], "nullable": not c[3], "pk": bool(c[5])} for c in cols]
        })

    conn.close()
    return schema
"""
CSV import: takes uploaded CSV bytes, auto-detects column types,
creates a SQLite database with the data as a queryable table.
Imported DBs are stored in memory registry alongside sample DBs.
"""
import csv
import io
import os
import re
import sqlite3
import uuid
from typing import Optional

DB_DIR = "./sample_dbs"

# Runtime registry of user-uploaded databases
# { db_id: { "name": display_name, "path": path, "table": table_name, "rows": N } }
USER_DATABASES: dict[str, dict] = {}


def import_csv(file_bytes: bytes, filename: str) -> dict:
    """
    Parse CSV, infer types, create SQLite DB, register it.
    Returns: { id, name, table, rows, columns }
    """
    os.makedirs(DB_DIR, exist_ok=True)

    # Decode
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file is empty or has no data rows")

    headers = list(rows[0].keys())
    if not headers:
        raise ValueError("CSV has no columns")

    # Sanitize column names (no spaces, no special chars)
    safe_headers = [_safe_col(h) for h in headers]

    # Infer column types from first 100 rows
    col_types = _infer_types(rows[:100], headers)

    # Build DB
    db_id = str(uuid.uuid4())[:8]
    display_name = os.path.splitext(filename)[0][:40]
    table_name = _safe_col(display_name) or "data"
    db_path = f"{DB_DIR}/user_{db_id}.db"

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # CREATE TABLE
    col_defs = ", ".join(
        f'"{safe_headers[i]}" {col_types[headers[i]]}'
        for i in range(len(headers))
    )
    c.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

    # INSERT rows
    placeholders = ", ".join(["?"] * len(headers))
    for row in rows:
        values = []
        for h, safe, orig in zip(headers, safe_headers, headers):
            raw = row.get(h, "")
            values.append(_coerce(raw, col_types[h]))
        c.execute(f'INSERT INTO "{table_name}" VALUES ({placeholders})', values)

    conn.commit()
    conn.close()

    # Register
    USER_DATABASES[db_id] = {
        "name": display_name,
        "path": db_path,
        "table": table_name,
        "rows": len(rows),
        "columns": [{"name": safe_headers[i], "original": headers[i], "type": col_types[headers[i]]}
                    for i in range(len(headers))],
    }

    return {
        "id": db_id,
        "name": display_name,
        "table": table_name,
        "rows": len(rows),
        "columns": safe_headers,
    }


def get_user_db_path(db_id: str) -> str:
    if db_id not in USER_DATABASES:
        raise ValueError(f"Uploaded database '{db_id}' not found (server may have restarted)")
    return USER_DATABASES[db_id]["path"]


def list_user_databases() -> list[dict]:
    return [
        {"id": k, "name": v["name"], "table": v["table"], "rows": v["rows"], "user_upload": True}
        for k, v in USER_DATABASES.items()
    ]


def delete_user_database(db_id: str):
    if db_id in USER_DATABASES:
        path = USER_DATABASES[db_id]["path"]
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        del USER_DATABASES[db_id]


# ── Type inference ────────────────────────────────────────────────────────────

def _infer_types(rows: list[dict], headers: list[str]) -> dict[str, str]:
    types = {}
    for h in headers:
        values = [row.get(h, "").strip() for row in rows if row.get(h, "").strip()]
        if not values:
            types[h] = "TEXT"
            continue
        if all(_is_int(v) for v in values):
            types[h] = "INTEGER"
        elif all(_is_float(v) for v in values):
            types[h] = "REAL"
        elif all(_is_date(v) for v in values):
            types[h] = "TEXT"  # store as text, SQLite date functions work on ISO strings
        else:
            types[h] = "TEXT"
    return types


def _is_int(v: str) -> bool:
    try: int(v.replace(",", "")); return True
    except: return False

def _is_float(v: str) -> bool:
    try: float(v.replace(",", "")); return True
    except: return False

def _is_date(v: str) -> bool:
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}', v) or re.match(r'^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', v))

def _coerce(v: str, t: str):
    if v is None or v.strip() == "":
        return None
    v = v.strip()
    try:
        if t == "INTEGER": return int(v.replace(",", ""))
        if t == "REAL":    return float(v.replace(",", ""))
    except Exception:
        pass
    return v

def _safe_col(name: str) -> str:
    s = re.sub(r'[^\w]', '_', name.strip())
    s = re.sub(r'_+', '_', s).strip('_')
    if s and s[0].isdigit():
        s = 'col_' + s
    return s or 'col'
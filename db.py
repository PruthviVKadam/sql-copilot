"""The DuckDB warehouse (P5's e-commerce dataset) + schema introspection.

Each call to connect() builds a fresh **in-memory** database from the committed Parquet, so
execution is sandboxed: a query can never touch a real file or persist anything.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

DATA = Path(__file__).resolve().parent / "data"
TABLES = ("customers", "orders", "order_items")


def connect() -> "duckdb.DuckDBPyConnection":
    con = duckdb.connect()  # ephemeral, in-memory
    for t in TABLES:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_parquet('{(DATA / (t + '.parquet')).as_posix()}')")
    return con


def schema(con) -> dict:
    """{table: [(col, type), ...]}."""
    out = {}
    for t in TABLES:
        out[t] = [(r[1], r[2]) for r in con.execute(f"PRAGMA table_info('{t}')").fetchall()]
    return out


def all_columns(sch: dict) -> set:
    return {c for cols in sch.values() for c, _ in cols}


def schema_prompt(con) -> str:
    """A compact schema + a few sample categorical values, for the LLM prompt."""
    sch = schema(con)
    lines = []
    for t, cols in sch.items():
        lines.append(f"TABLE {t}(" + ", ".join(f"{c} {ty}" for c, ty in cols) + ")")
    for t, col in (("orders", "status"), ("customers", "state"),
                   ("customers", "segment"), ("order_items", "category")):
        vals = [str(r[0]) for r in con.execute(
            f"SELECT DISTINCT {col} FROM {t} LIMIT 12").fetchall()]
        lines.append(f"-- {t}.{col} values: {', '.join(vals)}")
    return "\n".join(lines)


def run(con, sql: str):
    """Execute and return (columns, rows)."""
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()

"""The safety layer: parse with sqlglot, allow only a single read-only SELECT, block file-reading
functions, and force a row LIMIT. This is the part a compliance team cares about.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

ROW_LIMIT = 1000

# Functions that can touch the filesystem / mutate engine state — never allowed in a user query.
DENY_FUNCS = {"read_parquet", "read_csv", "read_csv_auto", "read_json", "read_json_auto",
              "parquet_scan", "csv_scan", "glob", "install", "load", "copy"}


@dataclass
class GuardResult:
    ok: bool
    reason: str
    safe_sql: str | None = None
    tables: set = field(default_factory=set)
    columns: set = field(default_factory=set)


def guard(sql: str) -> GuardResult:
    try:
        statements = [s for s in sqlglot.parse(sql, read="duckdb") if s is not None]
    except Exception as e:  # noqa: BLE001 — any parse failure is a rejection
        return GuardResult(False, f"could not parse SQL: {e}")

    if len(statements) != 1:
        return GuardResult(False, "only a single statement is allowed (no `;`-chained queries)")
    stmt = statements[0]

    if not isinstance(stmt, (exp.Select, exp.Union)):
        return GuardResult(False, f"only SELECT queries are allowed (got {type(stmt).__name__})")

    # typed table/scalar functions (e.g. ReadCSV, ReadParquet) — sql_name() == "READ_CSV"
    for fn in stmt.find_all(exp.Func):
        if (fn.sql_name() or "").lower() in DENY_FUNCS:
            return GuardResult(False, f"function `{fn.sql_name().lower()}` is not allowed")
    # unknown/anonymous functions (e.g. glob, parquet_scan)
    for fn in stmt.find_all(exp.Anonymous):
        if (fn.name or "").lower() in DENY_FUNCS:
            return GuardResult(False, f"function `{fn.name}` is not allowed")
    if stmt.find(exp.Copy):
        return GuardResult(False, "COPY is not allowed")

    tables = {t.name for t in stmt.find_all(exp.Table)}
    columns = {c.name for c in stmt.find_all(exp.Column)}

    if stmt.args.get("limit") is None and not stmt.find(exp.Group) is None:
        pass  # aggregates are naturally bounded, but we still cap below for safety
    if stmt.args.get("limit") is None:
        stmt = stmt.limit(ROW_LIMIT)

    return GuardResult(True, "ok", safe_sql=stmt.sql(dialect="duckdb"),
                       tables=tables, columns=columns)

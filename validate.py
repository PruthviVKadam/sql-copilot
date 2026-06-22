"""Hallucination detection: does the SQL actually bind against the schema, and do its results pass
basic sanity checks? Binding is judged by **DuckDB's own binder** (via `EXPLAIN`), which correctly
handles aliases, CTEs and qualified columns — far more reliable than matching names in the AST.
(Back-translation is an LLM-only extra; these checks are deterministic and key-free.)
"""
from __future__ import annotations


def schema_violations(safe_sql: str, con) -> list[str]:
    """Return binder errors (unknown table/column, type errors) — empty if the query binds cleanly.

    `EXPLAIN` plans the query without running it; a BinderException means a hallucinated reference.
    """
    try:
        con.execute("EXPLAIN " + safe_sql)
        return []
    except Exception as e:  # noqa: BLE001
        first = (str(e).strip().splitlines() or ["does not bind against the schema"])[0]
        return [first.strip()]


def result_sanity(columns, rows) -> list[str]:
    """Cheap post-execution checks that catch silently-wrong queries."""
    if not rows:
        return ["query returned 0 rows"]
    warnings = []
    for j, col in enumerate(columns):
        if all(r[j] is None for r in rows):
            warnings.append(f"column `{col}` is entirely NULL (often a bad JOIN)")
    return warnings


def confidence(guard_ok: bool, violations: list, sanity: list) -> float:
    """Composite: starts at 1.0, penalised by binder violations and sanity flags."""
    if not guard_ok:
        return 0.0
    return max(0.0, round(1.0 - 0.5 * bool(violations) - 0.15 * len(sanity), 2))

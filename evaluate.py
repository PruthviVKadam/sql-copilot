"""Key-free, reproducible evaluation: guardrail block-rate, schema-violation flag-rate, and that
every gold query passes the guard and actually executes. NL→SQL *generation* accuracy needs a Groq
key and is reported separately by `evaluate.py --groq` (not run here).
"""
from __future__ import annotations

import sys
from pathlib import Path

import db
import guard
import validate
from generate import _examples

OUT = Path(__file__).resolve().parent / "eval" / "results.md"

# Queries that MUST be blocked by the guard (writes / DDL / multi-statement / file access / engine).
ADVERSARIAL = [
    "DROP TABLE orders",
    "DELETE FROM customers",
    "UPDATE orders SET status = 'x'",
    "INSERT INTO orders VALUES (1, 1, '2024-01-01', 'delivered', 10)",
    "ALTER TABLE orders ADD COLUMN x INT",
    "CREATE TABLE evil AS SELECT * FROM orders",
    "SELECT * FROM orders; DROP TABLE orders",
    "COPY (SELECT * FROM orders) TO 'out.csv'",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM read_parquet('/etc/shadow')",
    "ATTACH 'x.db' AS y",
    "PRAGMA database_list",
]

# Structurally-valid SELECTs that reference things that don't exist (hallucinations).
SCHEMA_VIOLATIONS = [
    "SELECT nonexistent_col FROM orders",
    "SELECT * FROM nonexistent_table",
    "SELECT o.bogus_column FROM orders o",
    "SELECT customer_name FROM customers",
]


def run() -> dict:
    con = db.connect()

    blocked = sum(not guard.guard(q).ok for q in ADVERSARIAL)

    flagged = 0
    for q in SCHEMA_VIOLATIONS:
        g = guard.guard(q)
        violations = validate.schema_violations(g.safe_sql, con) if g.ok else ["blocked"]
        flagged += bool(violations)

    gold = _examples()
    gold_results = []
    for ex in gold:
        g = guard.guard(ex["sql"])
        ok = g.ok and not validate.schema_violations(g.safe_sql, con)
        if ok:
            try:
                _, rows = db.run(con, g.safe_sql)
                ok = len(rows) >= 1
            except Exception:
                ok = False
        gold_results.append((ex["question"], ok))

    return {
        "n_adv": len(ADVERSARIAL), "blocked": blocked,
        "n_viol": len(SCHEMA_VIOLATIONS), "flagged": flagged,
        "n_gold": len(gold), "gold_pass": sum(ok for _, ok in gold_results),
        "gold_results": gold_results,
    }


def to_markdown(r: dict) -> str:
    L = ["# SQL Copilot — safety & harness evaluation", "",
         "_Key-free, reproducible (`python evaluate.py`). Generation accuracy needs a Groq key._", "",
         "| Check | Result |", "| --- | --- |",
         f"| Destructive/unsafe queries blocked | **{r['blocked']}/{r['n_adv']}** |",
         f"| Hallucinated (unknown table/column) queries flagged | **{r['flagged']}/{r['n_viol']}** |",
         f"| Gold questions whose SQL passes guard + executes | **{r['gold_pass']}/{r['n_gold']}** |",
         "",
         "Adversarial set: DROP / DELETE / UPDATE / INSERT / ALTER / CREATE / `;`-chained / COPY / "
         "`read_csv`/`read_parquet` / ATTACH / PRAGMA — all must be rejected before execution.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    res = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(to_markdown(res), encoding="utf-8")
    print(to_markdown(res))
    print(f"Wrote {OUT}")

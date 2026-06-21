# 🛡️ SQL Copilot — natural language → SQL a compliance team would approve

Ask a question in plain English; get **safe, executed SQL** with the result, a confidence score, and
a hallucination check. Built over a real DuckDB warehouse with **guardrails** (no writes, row caps,
read-only) and **hallucination detection** — not a "the LLM wrote some SQL" toy.

> **Status:** scaffolding (plan + schedule below). Results table is a template filled only from the
> real eval run. Reuses the seeded e-commerce dataset from
> [Browser SQL Workbench](https://github.com/PruthviVKadam/sql-workbench) (P5) — same 170k-row schema.

## Problem → Approach → Result

- **Problem:** text-to-SQL is one of the highest-value AI features and one of the easiest to get
  dangerously wrong — it can hallucinate columns, write a query that *runs* but answers the wrong
  question, or (worse) mutate data. No serious company ships it without guardrails and validation.
- **Approach:** a **schema-aware** prompt (tables, types, keys, sample categorical values) →
  generate SQL with a structured output (SQL + explanation + tables touched) → run it through a
  **safety layer** (parse with `sqlglot`; block all DDL/DML writes; enforce `LIMIT`; reject scans
  above a row threshold) → **execute read-only** in DuckDB → **detect hallucination** by
  back-translating the SQL ("what question does this answer?") and sanity-checking results. Works
  **key-free** with a deterministic fallback; richer generation when a Groq key is present (like P3).
- **Result:** _(filled from the 50-question eval — no numbers until measured)_

| Metric | Value |
| --- | --- |
| Execution-match accuracy (50 hand-labeled Qs) | _TBD_ |
| Destructive operations blocked | _TBD_ (target 100%) |
| Hallucinated/way-off queries flagged | _TBD_ |

## Dataset
The committed Parquet from P5: `customers` (12,000) · `orders` (39,345) · `order_items` (118,293),
loaded into an in-process **DuckDB** warehouse. A real star-ish schema with joins, dates, and
categaries — enough to make text-to-SQL non-trivial.

## Stack

Python 3.14 · **DuckDB** · **sqlglot** (parse + guardrail enforcement) · Streamlit (or FastAPI) ·
Groq optional (OpenAI-compatible) with a key-free deterministic fallback.

## Reproduce (once built)

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python build_db.py        # load P5 parquet into a DuckDB warehouse
python eval.py            # 50 hand-labeled Qs -> execution-match + guardrail report
streamlit run app.py     # ask in English; see SQL, result, guardrail + hallucination flags
```

## Honesty guardrail

"Blocks 100% of destructive operations" is only claimed if `eval.py`'s guardrail suite proves it on
an adversarial query set. Execution-match and hallucination-flag rates are copied from the eval
output over a **hand-verified** golden set (the labels are written by a human, never by an LLM).

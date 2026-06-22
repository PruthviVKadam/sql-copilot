---
title: SQL Copilot
emoji: 🛡️
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# 🛡️ SQL Copilot — natural language → SQL a compliance team would approve

Ask a question in plain English; get **safe, executed SQL** with the result, a confidence score, and
a hallucination check. Built over a real DuckDB warehouse with **guardrails** (parse-time, not
prompt-time) and **binder-based hallucination detection** — not a "the LLM wrote some SQL" toy.

> Reuses the seeded e-commerce dataset from
> [Browser SQL Workbench](https://github.com/PruthviVKadam/sql-workbench) (P5): 12k customers ·
> 39k orders · 118k order-items. All numbers below come from `evaluate.py` (`eval/results.md`).

## Problem → Approach → Result

- **Problem:** text-to-SQL is high-value and easy to ship *dangerously* — it can mutate data,
  hallucinate columns, or run a query that's valid SQL but answers the wrong question. No serious
  team ships it without guardrails and validation.
- **Approach:** a **schema-aware** prompt → generate SQL (Groq when a key is set) → a **safety layer**
  (`sqlglot` parses the AST; only a single read-only `SELECT` is allowed; file-reading functions like
  `read_csv`/`read_parquet` are denied; a row `LIMIT` is injected) → execute in a sandboxed
  **in-memory** DuckDB → **hallucination detection** via DuckDB's own binder (`EXPLAIN`) + result
  sanity checks. Works **key-free** (template fallback) for the demo.
- **Result (real, key-free, from `evaluate.py`):**

| Check | Result |
| --- | --- |
| Destructive / unsafe queries **blocked** | **12 / 12** |
| Hallucinated (unknown table/column) queries **flagged** | **4 / 4** |
| Gold questions whose SQL passes the guard **and executes** | **15 / 15** |

_NL→SQL **generation accuracy** needs a Groq key and is **not** claimed here — the harness is ready
(`evaluate.py`), exactly as RAGAS is withheld in the 10-K RAG project until actually run._

## Insights

- **Safety is a *parsing* problem, not a *prompting* problem.** The guard blocks 100% of destructive
  ops by parsing the SQL and allowing only a single read-only `SELECT` — it never trusts the model to
  "promise" not to write. And `SELECT`-only isn't automatically safe: `read_csv`/`read_parquet` are
  `SELECT`s that read the filesystem, so they're denied explicitly (they parse as typed function
  nodes, not anonymous ones — a real gotcha I only caught by measuring).
- **Let the database judge hallucinations.** Matching column names in the AST false-flagged valid
  aliases and CTE-derived columns and dropped gold to 5/15. Delegating binding to **DuckDB's own
  binder** (`EXPLAIN`) is both simpler and correct — the engine already knows what resolves.
- **Generation is the swappable part; the guardrails + eval are the moat.** NL→SQL is one LLM call;
  what makes it shippable is that every query is parsed, capped, bind-checked, and sanity-checked
  before a human sees it — and that the whole pipeline is *measured*, not vibed.

## Stack

Python 3.14 · **DuckDB** · **sqlglot** (AST guardrails) · Streamlit · Groq (optional, OpenAI-compatible)
with a key-free template fallback. No torch.

## Reproduce

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python evaluate.py        # 12/12 blocked · 4/4 flagged · 15/15 gold execute -> eval/results.md
python -m pytest          # 7 tests pinning the guard + binder + gold suite
streamlit run app.py      # ask in English; see SQL, guardrail, hallucination check, result
```

Set `GROQ_API_KEY` (free at console.groq.com) for genuine NL→SQL; without it the app uses the
template fallback so the demo still runs.

## Files

```text
db.py        in-memory DuckDB warehouse (P5 parquet) + schema introspection
guard.py     sqlglot safety layer: single read-only SELECT, deny file funcs, inject LIMIT
validate.py  hallucination detection via DuckDB binder (EXPLAIN) + result sanity + confidence
generate.py  NL->SQL: Groq when keyed, else deterministic template fallback
evaluate.py  guardrail / schema-violation / gold suites -> eval/results.md
eval/gold.jsonl   15 hand-written (question, SQL) pairs
app.py       Streamlit UI incl. a "safety playground"
tests/       pytest (guard, binder, gold)
```

## Honesty guardrail

The headline is the **safety eval** (fully measurable without a key), not a generation-accuracy
number I can't reproduce here. Two findings came straight from measuring and were fixed, not hidden:
`read_csv`/`read_parquet` initially slipped the guard (10/12), and AST name-matching false-flagged
valid gold queries (5/15) — both visible in git history.

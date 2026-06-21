# Build Plan — SQL Copilot

## Interview thesis
"Text-to-SQL is easy to demo and hard to ship. I lead with **safety**: every generated query is
parsed and guardrailed (read-only, row-capped), executed in a sandbox, and validated for
hallucination via back-translation — then measured with execution-match on a hand-labeled set.
That's the bar a compliance team actually approves." Bridges P3 (LLM) and P5 (SQL).

## Architecture
```
build_db.py   load P5 parquet -> DuckDB warehouse (read-only role for serving)
schema.py     introspect tables/types/keys + sample categorical values for the prompt
generate.py   schema-aware prompt -> {sql, explanation, tables_used, confidence} (Groq or fallback)
guard.py      sqlglot parse; block DDL/DML; force LIMIT; reject row-scan > threshold (EXPLAIN)
validate.py   back-translate SQL->question; result sanity (range/row-count/NULL checks)
eval.py       50 hand-labeled Qs: execution-match + guardrail + hallucination metrics
app.py        Streamlit: NL box -> SQL + result table + confidence + flags
```

## Safety layers (defend each)
1. **Static guard (sqlglot):** parse the AST, reject anything that isn't a single `SELECT`; block
   `INSERT/UPDATE/DELETE/DROP/ALTER/ATTACH/COPY`; require/inject a `LIMIT`.
2. **Cost guard:** `EXPLAIN` the query; reject if estimated scan exceeds a row threshold.
3. **Sandbox:** execute against a **read-only** DuckDB connection — defense in depth even if a guard
   is bypassed.
4. **Hallucination detection:** back-translate the SQL to a question and compare to the original;
   run result sanity checks (implausible aggregates, all-NULL columns ⇒ likely bad JOIN). Optionally
   generate two independent queries and flag disagreement.

## Key decisions
- **Key-free fallback:** deterministic template/retrieval path so the demo always runs without a key
  (same philosophy as P3's extractive fallback). Groq only *upgrades* generation quality.
- **Eval = execution-match, not string-match:** two correct SQL strings can differ; compare result
  sets. The golden set includes joins, date filters, aggregations, ambiguity, and **unanswerable**
  questions (the model must say "I can't answer that from this schema").

## Phases (≈12 days, 2–3 h/day)
1. **Warehouse + schema introspection** — DuckDB load; schema/sample-value extractor for prompts.
2. **Generation** — structured SQL output; key-free fallback + optional Groq.
3. **Guardrails** — sqlglot static guard + EXPLAIN cost guard + read-only sandbox; adversarial tests.
4. **Hallucination detection** — back-translation + result sanity; composite confidence.
5. **Eval + app** — 50 hand-labeled Qs; Streamlit UI; real numbers in README.

## Py3.14 de-risk
DuckDB + sqlglot are pure-Python-friendly and already proven in P5's venv. No torch. Groq is an
HTTP call (no local model). Verify `sqlglot` parses a DuckDB dialect query before building the guard.

## Deploy
HF Spaces (Streamlit or Gradio SDK) or Streamlit Cloud. `GROQ_API_KEY` only via the host's secret
store — never committed (see `ManualSteps.md`).

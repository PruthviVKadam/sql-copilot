# Build Schedule — SQL Copilot (~12 days, 2–3 h/day)

| Day | Focus | Done when |
| --- | --- | --- |
| 1 | Repo, venv; load P5 parquet into DuckDB | `SELECT` works against all 3 tables |
| 2 | Schema introspection + sample categorical values | prompt context assembled programmatically |
| 3 | Generation (key-free fallback) | English question -> a runnable SELECT |
| 4 | Optional Groq path + structured output (sql/explanation/tables) | richer SQL when key present |
| 5 | sqlglot static guard (single SELECT, block writes, force LIMIT) | adversarial writes rejected |
| 6 | EXPLAIN cost guard + read-only sandbox connection | big-scan query blocked; writes impossible |
| 7 | Guardrail adversarial test set | 100% of destructive ops blocked in tests |
| 8 | Back-translation hallucination check | divergent SQL gets flagged |
| 9 | Result sanity checks + composite confidence | confidence reflects flags |
| 10 | Hand-write 50 golden Qs (joins/dates/aggs/ambiguous/unanswerable) | labels human-verified |
| 11 | `eval.py` execution-match + guardrail report; README real numbers | tests green; README filled |
| 12 | Streamlit app + deploy + 2-min walkthrough | live URL; recording done |

**Lead-with-the-number (resume line, once real):**
"__% execution-match on a 50-question hand-labeled set, blocks 100% of destructive operations, and
flags __% of hallucinated queries — text-to-SQL with the guardrails a compliance team requires."

**Cut scope if behind:** drop the two-query-agreement check and FastAPI; schema-aware generation +
static/cost guards + back-translation + the 50-Q eval is a complete, defensible project.

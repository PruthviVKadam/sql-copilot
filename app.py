"""SQL Copilot — natural language → guardrailed, executed SQL (Streamlit)."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

import db
import guard
import validate
from generate import _examples, generate

st.set_page_config(page_title="SQL Copilot", page_icon="🛡️", layout="wide")


@st.cache_resource(show_spinner="Loading warehouse…")
def get_con():
    return db.connect()


@st.cache_data
def get_schema_prompt():
    return db.schema_prompt(get_con())


con = get_con()
schema_prompt = get_schema_prompt()
has_key = bool(os.environ.get("GROQ_API_KEY"))

st.title("🛡️ SQL Copilot")
st.caption("Natural language → **safe, executed SQL** over a DuckDB e-commerce warehouse "
           "(12k customers · 39k orders · 118k items). Every query is parsed, capped, and "
           "bind-checked before it runs.")

with st.sidebar:
    st.header("Schema")
    st.code(schema_prompt, language="sql")
    st.markdown("**Generation:** " + ("🟢 Groq (LLM)" if has_key
                else "🟡 template-fallback — set `GROQ_API_KEY` for real NL→SQL"))

examples = [e["question"] for e in _examples()]
q = st.text_input("Ask a question", value=examples[2] if examples else "")
pick = st.selectbox("…or pick an example", [""] + examples)
question = pick or q

if question:
    sql, source = generate(question, schema_prompt)
    if not sql:
        st.error(f"Generation failed ({source}).")
        st.stop()

    st.markdown(f"**Generated SQL** · _{source}_")
    st.code(sql, language="sql")

    g = guard.guard(sql)
    if not g.ok:
        st.error(f"🚫 Blocked by guardrail: {g.reason}")
        st.stop()

    if g.safe_sql.strip() != sql.strip():
        st.caption(f"Guardrail applied a row cap → `{g.safe_sql}`")

    violations = validate.schema_violations(g.safe_sql, con)
    if violations:
        st.warning("🧠 Possible hallucination — the query does not bind against the schema: "
                   + "; ".join(violations))
        st.stop()

    cols, rows = db.run(con, g.safe_sql)
    sanity = validate.result_sanity(cols, rows)
    conf = validate.confidence(True, violations, sanity)

    c1, c2 = st.columns([1, 4])
    c1.metric("Confidence", f"{conf:.2f}")
    if sanity:
        c2.warning("Sanity: " + "; ".join(sanity))
    else:
        c2.success("Passed guardrails, binds to the schema, results look sane.")
    st.dataframe(pd.DataFrame(rows, columns=cols), use_container_width=True, height=360)

st.divider()
with st.expander("🛡️ Safety playground — try to break it"):
    st.caption("These should all be blocked *before* execution.")
    danger = st.selectbox("Pick an unsafe query", [
        "DROP TABLE orders", "DELETE FROM customers", "UPDATE orders SET status='x'",
        "SELECT * FROM orders; DROP TABLE orders", "SELECT * FROM read_csv('/etc/passwd')",
        "COPY (SELECT * FROM orders) TO 'out.csv'"])
    gd = guard.guard(danger)
    st.error(f"🚫 {gd.reason}") if not gd.ok else st.success("allowed")

st.caption("Educational demo. Safety is enforced by parsing (sqlglot) + DuckDB's binder, not by "
           "trusting the model — see the repo README for the eval (12/12 blocked, 15/15 gold execute).")

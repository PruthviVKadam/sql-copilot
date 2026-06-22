"""NL → SQL generation.

- **Groq** (OpenAI-compatible) when `GROQ_API_KEY` is set — real natural-language understanding.
- **Key-free fallback**: deterministic example-retrieval over the gold set, so the demo runs without
  a key. It does NOT understand novel questions — it returns the nearest known example's SQL. Set a
  key for genuine NL→SQL.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests

GOLD = Path(__file__).resolve().parent / "eval" / "gold.jsonl"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM = ("You are a careful analytics engineer. Translate the user's question into ONE DuckDB SQL "
          "SELECT over ONLY the given schema. Output just the SQL — no prose, no writes, no DDL.")


def _examples() -> list[dict]:
    if not GOLD.exists():
        return []
    return [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]


def _strip_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.+?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";").strip()


def groq_generate(question: str, schema_prompt: str, key: str) -> str:
    body = {"model": GROQ_MODEL, "temperature": 0,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"Schema:\n{schema_prompt}\n\nQuestion: {question}\nSQL:"}]}
    r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=30)
    r.raise_for_status()
    return _strip_sql(r.json()["choices"][0]["message"]["content"])


def _tok(s: str) -> set:
    return set(re.findall(r"[a-z]+", s.lower()))


def fallback_generate(question: str, examples: list[dict]) -> str | None:
    if not examples:
        return None
    q = _tok(question)
    return max(examples, key=lambda e: len(q & _tok(e["question"])) / (len(q | _tok(e["question"])) or 1))["sql"]


def generate(question: str, schema_prompt: str, key: str | None = None):
    """Return (sql, source) where source ∈ {'groq', 'template-fallback', 'groq-error: …'}."""
    key = key or os.environ.get("GROQ_API_KEY")
    if key:
        try:
            return groq_generate(question, schema_prompt, key), "groq"
        except Exception as e:  # noqa: BLE001
            return None, f"groq-error: {e}"
    return fallback_generate(question, _examples()), "template-fallback"

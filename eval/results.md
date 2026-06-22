# SQL Copilot — safety & harness evaluation

_Key-free, reproducible (`python evaluate.py`). Generation accuracy needs a Groq key._

| Check | Result |
| --- | --- |
| Destructive/unsafe queries blocked | **12/12** |
| Hallucinated (unknown table/column) queries flagged | **4/4** |
| Gold questions whose SQL passes guard + executes | **15/15** |

Adversarial set: DROP / DELETE / UPDATE / INSERT / ALTER / CREATE / `;`-chained / COPY / `read_csv`/`read_parquet` / ATTACH / PRAGMA — all must be rejected before execution.

"""Tests: the guard blocks everything unsafe, the binder catches hallucinations, and every gold
query passes the guard and executes. These pin the numbers in eval/results.md."""
import pytest

import db
import guard
import validate
from evaluate import ADVERSARIAL, SCHEMA_VIOLATIONS
from generate import _examples


@pytest.fixture(scope="module")
def con():
    return db.connect()


def test_all_adversarial_blocked():
    slipped = [q for q in ADVERSARIAL if guard.guard(q).ok]
    assert slipped == [], f"these unsafe queries were not blocked: {slipped}"


def test_read_file_functions_blocked():
    assert not guard.guard("SELECT * FROM read_parquet('x')").ok
    assert not guard.guard("SELECT * FROM read_csv('/etc/passwd')").ok


def test_simple_select_allowed_and_capped():
    g = guard.guard("SELECT * FROM orders")
    assert g.ok and "LIMIT" in (g.safe_sql or "").upper()


def test_existing_limit_not_doubled():
    g = guard.guard("SELECT * FROM orders LIMIT 5")
    assert g.ok and g.safe_sql.upper().count("LIMIT") == 1


def test_schema_violations_flagged_by_binder(con):
    for q in SCHEMA_VIOLATIONS:
        g = guard.guard(q)
        assert g.ok, q                                          # structurally a SELECT
        assert validate.schema_violations(g.safe_sql, con), q   # but does not bind


def test_all_gold_pass_and_execute(con):
    gold = _examples()
    assert len(gold) == 15
    for ex in gold:
        g = guard.guard(ex["sql"])
        assert g.ok, ex["question"]
        assert not validate.schema_violations(g.safe_sql, con), ex["question"]
        _, rows = db.run(con, g.safe_sql)
        assert len(rows) >= 1, ex["question"]


def test_confidence_zero_when_blocked():
    assert validate.confidence(False, [], []) == 0.0
    assert validate.confidence(True, ["unknown column"], []) < 0.6

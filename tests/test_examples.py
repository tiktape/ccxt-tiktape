import pathlib
import py_compile

import pytest

EXAMPLES = sorted((pathlib.Path(__file__).parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_compiles(path):
    py_compile.compile(str(path), doraise=True)


def test_examples_present():
    assert {p.name for p in EXAMPLES} >= {"past_5000_limit.py", "download_csv.py", "sma_crossover_backtest.py"}

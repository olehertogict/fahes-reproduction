"""Correctness checks for the FAHES wrapper, the ground truth and the scoring. Run: uv run pytest"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import datasets as D  # noqa: E402
from make_tables import aggregate_scores, as_set, canon_column, canon_value  # noqa: E402
from tools import FAHES_MODULES, parse_fahes_output, run_fahes  # noqa: E402


def test_fahes_output_with_comma_in_value(tmp_path):
    path = tmp_path / "DMV_t.csv"
    path.write_text("Table Name,Attribute Name,DMV,Frequency,Detecting Tool\nt,city,\"a,b\",3,SYN\nt,age,0,7,OD\n")
    out = parse_fahes_output(path)
    assert out.to_dict("records") == [{"column": "city", "value": "\"a,b\"", "frequency": 3, "tool": "SYN"},
                                      {"column": "age", "value": "0", "frequency": 7, "tool": "OD"}]


def test_values_and_columns_are_compared_canonically():
    assert canon_value(" 0") == canon_value("0.0") == canon_value("0")
    assert canon_value(" ?") == "?"
    assert canon_column("﻿OBJECTID ") == "OBJECTID"


def test_fahes_runs_every_module_on_an_official_data_file():
    path, _ = D.paper_example("pima")
    for module in FAHES_MODULES:
        result, seconds = run_fahes(path, module)
        assert list(result.columns) == ["column", "value", "frequency", "tool"] and seconds > 0
    assert ("Diastolic blood pressure", canon_value("0")) in as_set(run_fahes(path, "all")[0])


def test_macro_and_pooled_scores_use_different_denominators():
    runs = pd.DataFrame([
        {"hits": 1, "reported": 1, "truth": 1, "precision": 1.0, "recall": 1.0},
        {"hits": 1, "reported": 9, "truth": 3, "precision": 1 / 9, "recall": 1 / 3},
        {"hits": 0, "reported": 0, "truth": 1, "precision": float("nan"), "recall": 0.0},
    ])
    result = aggregate_scores(runs)
    assert result["macro_precision"] == pytest.approx(5 / 9)
    assert result["macro_recall"] == pytest.approx(4 / 9)
    assert result["pooled_precision"] == pytest.approx(2 / 10)
    assert result["pooled_recall"] == pytest.approx(2 / 5)
    assert result["precision_defined"] == 2


def test_documented_codes_are_in_the_data():
    for name in D.DOCUMENTED:
        path, truth = D.documented(name)
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        for column, value, _ in truth:
            assert (df[column].str.strip() == value).any(), (name, column, value)


def test_changed_cached_data_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "DATA_DIR", tmp_path)
    source = tmp_path / "uci" / "mushroom" / "agaricus-lepiota.data"
    source.parent.mkdir(parents=True)
    source.write_text("changed dataset\n")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        D.documented("mushroom")
    assert not (tmp_path / "mushroom.csv").exists()


def test_paper_examples_are_in_the_official_data_files():
    for name in D.PAPER_EXAMPLES:
        path, truth = D.paper_example(name)
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1")
        for column, value, _ in truth:
            assert (df[column].str.strip() == value).any(), (name, column, value)

"""Small tests for qualitycheck on real public data.

tests/data/gtex_subjects_first40.txt is the first 40 rows of the GTEx v11
SubjectPhenotypesDS.txt file (open access). tests/data/hubmap_result.json is a
saved run on the public HuBMAP donor table.

Run with:  python -m pytest tests
"""
import json
import os
import subprocess
import sys

import openpyxl
import pandas as pd

from qualitycheck.checks import TableSpec, profile
from qualitycheck.fetch import read_text_table
from qualitycheck.limits import load_limits
from qualitycheck.report import build

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GTEX = os.path.join(HERE, "data", "gtex_subjects_first40.txt")
SPEC = TableSpec(required=["SUBJID", "SEX", "AGE"], ids=["SUBJID"])


def counts(df):
    checks, _, miss = profile(df, SPEC, "test")
    return {c.name.split(" (")[0]: c.problems for c in checks}, miss


def test_clean_file():
    df = read_text_table(GTEX, sep="\t")
    assert len(df) == 40
    found, miss = counts(df)
    assert miss["required_cells"] == 120
    assert miss["required_missing"] == 0
    assert found["Rows that are exact copies of another row"] == 0
    assert found['Repeated IDs in "SUBJID"'] == 0


def test_problems_are_counted():
    # the same rows with SEX blanked, AGE set to NA and one row repeated
    df = read_text_table(GTEX, sep="\t")
    df.loc[0, "SEX"] = ""
    df.loc[1, "AGE"] = "NA"
    df = pd.concat([df, df.iloc[[5]]], ignore_index=True)
    found, miss = counts(df)
    assert miss["required_missing"] == 2
    assert found["Rows that are exact copies of another row"] == 1
    assert found['Repeated IDs in "SUBJID"'] == 1


def test_limits_file():
    lim = load_limits()
    for rule in lim["rules"].values():
        assert rule["pass"] <= rule["fail"]


def test_command_line(tmp_path):
    out = tmp_path / "r.json"
    run = subprocess.run([sys.executable, "-m", "qualitycheck", "file", GTEX,
                          "--required", "SUBJID,SEX,AGE", "--ids", "SUBJID", "--json", str(out)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert "40 rows" in run.stdout
    assert json.loads(out.read_text())["missing"]["required_missing"] == 0


def test_workbook(tmp_path):
    res = tmp_path / "results"
    res.mkdir()
    (res / "hubmap.json").write_text(open(os.path.join(HERE, "data", "hubmap_result.json")).read())
    path = build(res, tmp_path / "out.xlsx")
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["Summary", "Missing values", "Checks", "Columns", "Method", "Sources"]
    assert wb["Summary"]["A5"].value == "HuBMAP"
    assert wb["Checks"]["K5"].value.startswith("=IF(")

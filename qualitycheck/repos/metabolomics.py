"""Metabolomics Workbench: metabolite values and sample factors from the REST API.

The study list is the 11 studies picked for the CFDE review. Four of them
return no named-metabolite data from the REST API (ST000306, ST001434,
ST003733, ST003928), so the tables hold the other 7.
"""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import get_json, records_to_table, repo_dir
from ..table import Table

NAME = "Metabolomics Workbench"
WHAT = "Repository data"
DATA = "Metabolite values and sample factors for the selected studies (REST API)."
REST = "https://www.metabolomicsworkbench.org/rest/study/study_id/"
STUDIES = ["ST000306", "ST001434", "ST003733", "ST003928", "ST004519", "ST003938", "ST003932",
           "ST003929", "ST003595", "ST002736", "ST002732"]
KEY_WHY = ("Key fields: the repository does not publish a required-field list, so only the "
           "ID or key needed to use each record is treated as required.")


def _entries(data):
    """The API gives one object for a single hit and a numbered dict for many."""
    if not data:
        return []
    if isinstance(data, dict) and "study_id" in data:
        return [data]
    return list(data.values())


def tables():
    d = repo_dir("metabolomics")
    values, factors, with_data = [], [], []
    for st in STUDIES:
        rows = _entries(get_json(REST + st + "/data", cache=d / f"{st}_data.json"))
        if not rows:
            continue
        with_data.append(st)
        for r in rows:
            for sample, v in (r.get("DATA") or {}).items():
                values.append({"study_id": r.get("study_id"), "analysis_id": r.get("analysis_id"),
                               "metabolite_name": r.get("metabolite_name"),
                               "metabolite_id": r.get("metabolite_id"),
                               "refmet_name": r.get("refmet_name"), "units": r.get("units"),
                               "sample": sample, "value": v})
        factors += _entries(get_json(REST + st + "/factors", cache=d / f"{st}_factors.json"))
    n = len(with_data)
    skipped = [s for s in STUDIES if s not in with_data]
    note = (f"Studies checked: {', '.join(with_data)}. No metabolite data from the REST API: "
            f"{', '.join(skipped) or 'none'}.")
    yield Table(f"Metabolite values (REST API, {n} studies with data)", REST + "ST004519/data",
                df=records_to_table(values), spec=TableSpec(
                    required=["study_id", "analysis_id", "metabolite_name", "sample", "value"],
                    required_why=KEY_WHY,
                    keys=[["study_id", "analysis_id", "metabolite_name", "sample"]],
                    formats=[("study_id", "ST000000", r"ST\d{6}"),
                             ("metabolite_id", "ME + digits", r"ME\d+"),
                             ("value", "number", F.NUMBER)],
                    note=note))
    yield Table(f"Sample factors (REST API, {n} studies with data)", REST + "ST004519/factors",
                df=records_to_table(factors, columns=["study_id", "local_sample_id",
                                                      "sample_source", "factors",
                                                      "mb_sample_id", "raw_data"]),
                spec=TableSpec(required=["study_id", "local_sample_id"], required_why=KEY_WHY,
                               keys=[["study_id", "local_sample_id"]],
                               formats=[("mb_sample_id", "SA + digits", r"SA\d+")], note=note))

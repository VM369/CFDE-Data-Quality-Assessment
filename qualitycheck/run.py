"""Run the checks for one repository and save results/<repo>.json."""

import importlib
import json
import time
from pathlib import Path

from .checks import profile, profile_matrix
from .limits import load_limits, missing_score, worst

# Same order as the CFDE evaluation matrix
REPOS = ["fourdn", "exrna", "gtex", "glygen", "ai_readi", "bridge2ai_voice", "chorus",
         "cm4ai", "hubmap", "kids_first", "lincs", "metabolomics", "motrpac", "sparc",
         "sennet", "hmp", "idg", "impc", "scge", "a2cps", "nph", "smaht"]

RESULTS_DIR = Path("results")


def run_repo(key, limits=None):
    limits = limits or load_limits()
    mod = importlib.import_module(f".repos.{key}", __package__)
    out = {"key": key, "repository": mod.NAME, "what": mod.WHAT, "data": mod.DATA,
           "tables": [], "sources": []}
    if getattr(mod, "NOT_TESTED", False):
        out["not_tested"] = True
        out["sources"].append({"table": "No public data", "url": mod.SOURCE})
        return out
    t0 = time.time()
    for t in mod.tables():
        if t.matrix is not None:
            checks, n_rows, miss = profile_matrix(**t.matrix)
            cols = []
        else:
            checks, cols, miss = profile(t.df, t.spec, t.label)
            n_rows = len(t.df)
        rows = [c.as_dict(limits) for c in checks]
        miss["score"] = missing_score(miss["required_cells"], miss["required_missing"],
                                      miss["optional_cells"], miss["optional_missing"], limits)
        out["tables"].append({"table": t.label, "source": t.source, "rows": n_rows,
                              "checks": rows, "columns": cols, "missing": miss})
        out["sources"].append({"table": t.label, "url": t.source})
        print(f"  {t.label}: {n_rows:,} rows, {len(rows)} checks, "
              f"{sum(r['result'] not in ('Pass', 'No records') for r in rows)} not Pass")
    out["seconds"] = round(time.time() - t0, 1)
    return out


def summarize(res):
    if res.get("not_tested"):
        return {"repository": res["repository"], "result": "Not tested"}
    allc = [c for t in res["tables"] for c in t["checks"]]
    area = {a: worst([c["result"] for c in allc if c["area"] == a])
            for a in ("Missing values", "Duplicates", "Standard format")}
    rc = sum(t["missing"]["required_cells"] for t in res["tables"])
    rm = sum(t["missing"]["required_missing"] for t in res["tables"])
    oc = sum(t["missing"]["optional_cells"] for t in res["tables"])
    om = sum(t["missing"]["optional_missing"] for t in res["tables"])
    return {"repository": res["repository"], "tables": len(res["tables"]),
            "rows": sum(t["rows"] for t in res["tables"]), "checks": len(allc),
            "not_pass": sum(c["result"] not in ("Pass", "No records") for c in allc),
            "required_cells": rc, "required_missing": rm,
            "optional_cells": oc, "optional_missing": om, **area}


def save(res):
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{res['key']}.json"
    path.write_text(json.dumps(res, indent=1))
    return path

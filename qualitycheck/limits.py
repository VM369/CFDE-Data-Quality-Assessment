"""Pass and Fail limits, and the missing values score.

These are working numbers for the CFDE review, not a published standard.
Change them in limits.json (same folder as this file) and run again.
"""

import json
from pathlib import Path

LIMITS_FILE = Path(__file__).with_name("limits.json")


def load_limits(path=None):
    with open(path or LIMITS_FILE) as fh:
        return json.load(fh)


def result_for(rule, records, pct, limits):
    if records == 0:
        return "No records"
    lim = limits["rules"][rule]
    if pct <= lim["pass"]:
        return "Pass"
    if pct > lim["fail"]:
        return "Fail"
    return "Check"


def worst(results):
    results = [r for r in results if r not in ("No records", None)]
    if not results:
        return "No records"
    for r in ("Fail", "Check"):
        if r in results:
            return r
    return "Pass"


def missing_score(req_cells, req_missing, opt_cells, opt_missing, limits):
    """100 x weighted share of filled cells. Optional part left out if there are none."""
    w = limits["score_weights"]
    parts = []
    if req_cells:
        parts.append((w["required"], 1 - req_missing / req_cells))
    if opt_cells:
        parts.append((w["optional"], 1 - opt_missing / opt_cells))
    if not parts:
        return None
    return 100 * sum(a * b for a, b in parts) / sum(a for a, _ in parts)

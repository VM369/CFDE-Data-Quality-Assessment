"""LINCS: L1000 signature records from the SigCom LINCS metadata API."""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import get_json, records_to_table, repo_dir
from ..table import Table

NAME = "LINCS"
WHAT = "Repository data"
DATA = "SigCom LINCS L1000 chemical perturbation signatures (first 20,000 records, sorted by ID)."
URL = "https://maayanlab.cloud/sigcom-lincs/metadata-api/signatures/find"
# L1000 chemical perturbation signatures (LINCS DCIC)
LIBRARY = "54198d6e-fe17-5ef8-91ac-02b425761653"
LIMIT = 20000
PAGE = 1000

DOSE = F.NUMBER + r" ?[a-zA-Zµ%/]+"
TIME = F.NUMBER + r" ?h"


def tables():
    d = repo_dir("lincs")
    rows = []
    # Without a sort order the API returns records in a different order each time,
    # so the records are sorted by ID to make the run repeatable.
    for skip in range(0, LIMIT, PAGE):
        page = get_json(URL, method="POST", body={"filter": {"limit": PAGE, "skip": skip, "order": "id",
                                                      "where": {"library": LIBRARY}}},
                        cache=d / f"signatures_{skip}.json")
        for s in page:
            meta = {k: v for k, v in s.get("meta", {}).items() if not k.startswith("$")}
            rows.append({"id": s["id"], "library": s["library"], **meta})
        if len(page) < PAGE:
            break
    df = records_to_table(rows)
    spec = TableSpec(
        required=["id", "library", "local_id"],
        required_why=("Key fields: the repository does not publish a required-field list, so "
                      "only the ID or key needed to use each record is treated as required."),
        ids=["id"], keys=[["local_id"]],
        formats=[("md5", "32 hex", F.MD5), ("doid", "DOID:N", F.DOID),
                 ("sha256", "64 hex", F.SHA256), ("anatomy", "UBERON:0000000", F.term("UBERON")),
                 ("pert_dose", "number + unit", DOSE), ("pert_time", "number + h", TIME),
                 ("creation_time", "ISO 8601", F.iso_date),
                 ("size_in_bytes", "whole number", F.WHOLE_POS)])
    yield Table("SigCom LINCS L1000 chemical signatures (first 20,000 by ID)", URL, df=df, spec=spec)

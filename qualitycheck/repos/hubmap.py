"""HuBMAP: public donor records from the HuBMAP search API."""

from ..checks import TableSpec
from ..fetch import get_json, repo_dir
from ..table import Table
from ._donors import donor_row, donor_table, number_formats

NAME = "HuBMAP"
WHAT = "Public metadata only"
DATA = "Donor metadata for all public HuBMAP donors (age, sex, race, BMI, height, weight)."
URL = "https://search.api.hubmapconsortium.org/v3/portal/search"


def tables():
    body = {"size": 10000, "query": {"term": {"entity_type.keyword": "Donor"}},
            "_source": ["hubmap_id", "group_name", "metadata"]}
    hits = get_json(URL, method="POST", body=body, cache=repo_dir("hubmap") / "donors.json")
    rows = [donor_row(h["_source"]["hubmap_id"], h["_source"].get("group_name", ""),
                      h["_source"].get("metadata")) for h in hits["hits"]["hits"]]
    spec = TableSpec(
        required=["id", "group", "Age", "Sex", "Race"],
        required_why=("HuBMAP donor minimum is age, race and sex "
                      "(https://pmc.ncbi.nlm.nih.gov/articles/PMC13321327.2/); every donor has a "
                      "HuBMAP ID and a group (https://docs.hubmapconsortium.org/donor.html)."),
        ids=["id"], formats=number_formats(),
        note="One row per donor. Main fields only (age, sex, race, ethnicity, BMI, height, "
             "weight, cause of death).")
    yield Table("Donor metadata (all public)", URL, df=donor_table(rows), spec=spec)

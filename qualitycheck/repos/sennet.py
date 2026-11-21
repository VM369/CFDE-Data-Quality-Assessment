"""SenNet: public human source (donor) records from the SenNet search API."""

from ..checks import TableSpec
from ..fetch import get_json, repo_dir
from ..table import Table
from ._donors import donor_row, donor_table, number_formats

NAME = "SenNet"
WHAT = "Public metadata only"
DATA = "Human source (donor) metadata for all public SenNet donors."
URL = "https://search.api.sennetconsortium.org/entities/search"


def tables():
    body = {"size": 10000, "query": {"term": {"entity_type.keyword": "Source"}},
            "_source": ["sennet_id", "group_name", "source_type", "metadata"]}
    hits = get_json(URL, method="POST", body=body, cache=repo_dir("sennet") / "sources.json")
    rows = [donor_row(h["_source"]["sennet_id"], h["_source"].get("group_name", ""),
                      h["_source"].get("metadata"))
            for h in hits["hits"]["hits"] if h["_source"].get("source_type") == "Human"]
    spec = TableSpec(
        required=["id", "group", "Age", "Sex", "Race", "Ethnicity"],
        required_why=("SenNet material transfer agreement asks for age, sex, race and ethnicity "
                      "of each donor (https://sennetconsortium.org/mta/); id and group identify "
                      "the record."),
        ids=["id"], formats=number_formats(),
        note=f"One row per donor. Main fields only (age, sex, race, ethnicity, BMI, height, "
             f"weight, cause of death). Human sources only ({len(rows)} of "
             f"{len(hits['hits']['hits'])}). The rest are mouse sources.")
    yield Table("Human source (donor) metadata (all public)", URL, df=donor_table(rows), spec=spec)

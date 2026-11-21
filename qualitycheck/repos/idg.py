"""IDG: all Pharos targets from the Pharos GraphQL API."""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import get_json, records_to_table, repo_dir
from ..table import Table

NAME = "IDG"
WHAT = "Repository data"
DATA = "All Pharos targets (name, symbol, UniProt, development level, family, novelty)."
URL = "https://pharos-api.ncats.io/graphql"
PAGE = 5000
QUERY = "{targets{count targets(top:%d, skip:%d){name sym uniprot tdl fam novelty}}}"
# Target development levels (https://pharos.nih.gov/about)
TDL = {"Tclin", "Tchem", "Tbio", "Tdark"}


def tables():
    d = repo_dir("idg")
    rows, skip, total = [], 0, None
    while total is None or skip < total:
        data = get_json(URL, method="POST", body={"query": QUERY % (PAGE, skip)},
                        cache=d / f"targets_{skip}.json")["data"]["targets"]
        total = data["count"]
        rows += data["targets"]
        skip += PAGE
    df = records_to_table(rows, columns=["name", "sym", "uniprot", "tdl", "fam", "novelty"])
    spec = TableSpec(
        required=["uniprot", "name"],
        required_why=("Pharos GraphQL schema marks Target.uniprot and Target.name as NON_NULL "
                      "(https://pharos-api.ncats.io/graphql)."),
        ids=["uniprot"],
        formats=[("uniprot", "UniProt accession", F.UNIPROT), ("novelty", "number", F.NUMBER)],
        allowed={"tdl": (TDL, "IDG target development levels")})
    yield Table("Pharos targets (all)", URL, df=df, spec=spec)

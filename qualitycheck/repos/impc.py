"""KOMP2 (IMPC): every total cholesterol record from the IMPC Solr API."""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import get_json, records_to_table, repo_dir
from ..table import Table

NAME = "KOMP2 (IMPC)"
WHAT = "Repository data"
DATA = "All IMPC total cholesterol measurements (parameter IMPC_CBC_015_001)."
SOLR = "https://www.ebi.ac.uk/mi/impc/solr/experiment/select"
URL = SOLR + "?q=parameter_stable_id:IMPC_CBC_015_001"
PAGE = 20000
COLUMNS = ["observation_id", "specimen_id", "external_sample_id", "phenotyping_center", "sex",
           "zygosity", "biological_sample_group", "strain_name", "gene_symbol",
           "allele_accession_id", "date_of_experiment", "date_of_birth", "age_in_days", "weight",
           "data_point", "metadata_group", "experiment_id", "unit_x", "unit_y",
           "datasource_name", "life_stage_name"]
# Allowed values as used in the IMPC data (https://www.mousephenotype.org/help/)
ALLOWED = {"sex": ({"male", "female"}, "IMPC"),
           "zygosity": ({"homozygote", "heterozygote", "hemizygote", "wildtype"}, "IMPC"),
           "biological_sample_group": ({"control", "experimental"}, "IMPC")}


def tables():
    d = repo_dir("impc")
    rows, start, total = [], 0, None
    while total is None or start < total:
        params = {"q": "parameter_stable_id:IMPC_CBC_015_001", "fl": ",".join(COLUMNS),
                  "rows": PAGE, "start": start, "sort": "observation_id asc", "wt": "json"}
        res = get_json(SOLR, params=params, cache=d / f"page_{start}.json")["response"]
        total = res["numFound"]
        rows += res["docs"]
        start += PAGE
    df = records_to_table(rows, columns=COLUMNS)
    spec = TableSpec(
        required=["observation_id", "specimen_id", "sex", "zygosity",
                  "biological_sample_group", "data_point"],
        required_why=("Key fields: the repository does not publish a required-field list, so "
                      "only the ID or key needed to use each record is treated as required (a "
                      "measurement is not usable without the mouse, its sex, zygosity, "
                      "control/experimental group and the value)."),
        ids=["observation_id"], allowed=ALLOWED,
        formats=[("allele_accession_id", "MGI:N", F.MGI),
                 ("date_of_experiment", "ISO 8601", F.iso_datetime),
                 ("date_of_birth", "ISO 8601", F.iso_datetime),
                 ("age_in_days", "whole number", F.WHOLE_POS),
                 ("weight", "number", F.NUMBER), ("data_point", "number", F.NUMBER)])
    yield Table("Total cholesterol records (IMPC_CBC_015_001, all)", URL, df=df, spec=spec)

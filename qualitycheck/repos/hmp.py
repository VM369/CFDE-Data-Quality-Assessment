"""HMP: HMP2 (iHMP IBD) sample metadata from the IBDMDB."""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import download, read_text_table, repo_dir
from ..table import Table

NAME = "HMP"
WHAT = "Repository data"
DATA = "HMP2 (iHMP IBD) sample metadata, one row per sample per data type."
PORTAL = "https://ibdmdb.org/"
# Link from the IBDMDB results page (files are served through Globus)
FILE = ("https://g-227ca.190ebd.75bc.data.globus.org/ibdmdb/metadata/"
        "hmp2_metadata_2018-08-20.csv")
# whole numbers may be written with a trailing .0 by the export; weeks before baseline are negative
WHOLE = r"[+-]?\d+(\.0+)?"


def tables():
    df = read_text_table(download(FILE, repo_dir("hmp") / "hmp2_metadata_2018-08-20.csv"))
    spec = TableSpec(
        required=["External ID", "Participant ID", "data_type"],
        required_why=("Key fields: the repository does not publish a required-field list, so "
                      "only the ID or key needed to use each record is treated as required."),
        keys=[["External ID", "data_type"]],
        formats=[("week_num", "whole number", WHOLE),
                 ("date_of_receipt", "YYYY-MM-DD", F.iso_date),
                 ("reads_raw", "whole number", WHOLE),
                 ("consent_age", "number", F.NUMBER)],
        note=("From the IBDMDB, the HMP2 data portal (hmp2_metadata_2018-08-20.csv). One row per "
              "sample per data type, so many questionnaire columns only apply to some rows."))
    yield Table("HMP2 (iHMP IBD) sample metadata", PORTAL, df=df, spec=spec)

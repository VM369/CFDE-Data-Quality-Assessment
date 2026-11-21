"""SMaHT: all public file records from the SMaHT data portal."""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import get_json, records_to_table, repo_dir
from ..table import Table

NAME = "SMaHT"
WHAT = "Public metadata only"
DATA = "All public SMaHT file listings (format, type, size, checksums)."
SEARCH = "https://data.smaht.org/search/"
URL = SEARCH + "?type=File"
FIELDS = ["accession", "filename", "file_format.display_title", "data_type", "data_category",
          "file_size", "md5sum", "content_md5sum", "status", "access_status", "date_created"]


def tables():
    params = [("type", "File"), ("limit", "all"), ("format", "json")] + [("field", f) for f in FIELDS]
    graph = get_json(SEARCH, params=params, cache=repo_dir("smaht") / "files.json")["@graph"]
    rows = []
    for g in graph:
        r = {f: g.get(f) for f in FIELDS if "." not in f}
        r["file_format"] = (g.get("file_format") or {}).get("display_title")
        rows.append(r)
    df = records_to_table(rows, columns=["accession", "filename", "file_format", "data_type",
                                         "data_category", "file_size", "md5sum",
                                         "content_md5sum", "status", "access_status",
                                         "date_created"])
    spec = TableSpec(
        required=["accession", "data_category", "data_type", "file_format"],
        required_why=("SMaHT File schema requires data_category, data_type and file_format "
                      "(https://data.smaht.org/profiles/File.json); accession is the record ID."),
        ids=["accession"],
        formats=[("accession", "SMAxx + 7 characters", F.SMAHT_ACCESSION),
                 ("file_size", "whole number", F.WHOLE_POS), ("md5sum", "32 hex", F.MD5),
                 ("content_md5sum", "32 hex", F.MD5), ("date_created", "ISO 8601", F.iso_datetime)])
    yield Table(f"File records (all {len(df):,} public listings)", URL, df=df, spec=spec)

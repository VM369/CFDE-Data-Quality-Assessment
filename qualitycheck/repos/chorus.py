"""CHoRUS: RO-Crate metadata of the public release (UVA Dataverse).

The clinical data sits behind a data use agreement, so only the public
metadata can be checked. Rules: RO-Crate 1.1 root data entity
(https://www.researchobject.org/ro-crate/specification/1.1/root-data-entity.html).
"""

import json

from .. import formats as F
from ..checks import Check, TableSpec, missing_masks
from ..fetch import download, get_json, records_to_table, repo_dir
from ..table import Table

NAME = "CHoRUS (Clinical Care)"
WHAT = "Public metadata only"
DATA = "RO-Crate metadata of the public release. Clinical data is under a data use agreement."
DOI = "https://doi.org/10.18130/V3/ATG0DP"
API = "https://dataverse.lib.virginia.edu/api/datasets/:persistentId/?persistentId=doi:10.18130/V3/ATG0DP"
ROOT_PROPS = ["name", "description", "datePublished", "license"]


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def dataset_props(df):
    ds = df[df["@type"].str.contains("Dataset", na=False)]
    missing = 0
    for p in ROOT_PROPS:
        if p not in df.columns:
            missing += len(ds)
            continue
        e, h = missing_masks(ds[p])
        missing += int((e | h).sum())
    return [Check("Missing values", "Missing required",
                  f"Dataset entities ({len(ds)}) missing a required property: " + ", ".join(ROOT_PROPS),
                  len(ds) * len(ROOT_PROPS), missing,
                  "RO-Crate 1.1 root data entity must have name, description, datePublished "
                  "and license (https://www.researchobject.org/ro-crate/specification/1.1/"
                  "root-data-entity.html).")]


def tables():
    d = repo_dir("chorus")
    files = get_json(API, cache=d / "dataset.json")["data"]["latestVersion"]["files"]
    fid = next(f["dataFile"]["id"] for f in files if f["dataFile"]["filename"] == "ro-crate-metadata.json")
    url = f"https://dataverse.lib.virginia.edu/api/access/datafile/{fid}"
    graph = json.loads(download(url, d / "ro-crate-metadata.json").read_text())["@graph"]
    df = records_to_table([{k: _cell(v) for k, v in e.items()} for e in graph])
    spec = TableSpec(required=["@id", "@type"],
                     required_why="RO-Crate 1.1: every entity needs @id and @type "
                                  "(https://www.researchobject.org/ro-crate/specification/1.1/); "
                                  "dataset entities are checked separately for name, description, "
                                  "datePublished and license.",
                     ids=["@id"],
                     formats=[("datePublished", "ISO 8601, RO-Crate 1.1", F.iso_date)],
                     extra=[dataset_props],
                     note="Only public metadata. Clinical data is under a data use agreement.")
    yield Table("RO-Crate entities (public metadata)", DOI, df=df, spec=spec)

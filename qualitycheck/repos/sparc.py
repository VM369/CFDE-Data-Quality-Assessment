"""SPARC: subjects and samples files from every public SPARC dataset.

Each SPARC dataset follows the SPARC Dataset Structure (SDS) and has a
subjects file and often a samples file in its files/ folder. The files are
read from the Pennsieve Discover service, one dataset at a time.
"""

import io
import re
import zipfile


import pandas as pd

from ..checks import TableSpec
from ..fetch import download_post, get_json, read_text_table, repo_dir
from ..table import Table

NAME = "SPARC"
WHAT = "Repository data"
DATA = "SDS subjects and samples files from all public SPARC datasets (Pennsieve Discover)."
API = "https://api.pennsieve.io/discover"
URL = API + "/datasets"
ORGS = {"SPARC", "SPARC Consortium"}

SUBJECT_COLS = ["subject_id", "pool_id", "species", "sex", "age", "age_category", "strain",
                "rrid_for_strain", "body_mass", "age_range_min", "age_range_max"]
SAMPLE_COLS = ["subject_id", "sample_id", "pool_id", "sample_type",
               "sample_anatomical_location", "was_derived_from"]
# Older SDS templates used other names for the same sample columns
OLD_NAMES = {"specimen_type": "sample_type",
             "specimen_anatomical_location": "sample_anatomical_location",
             "wasderivedfromsample": "was_derived_from"}

NOTE = ("Main SPARC Dataset Structure (SDS) columns only. Each dataset file read as-is from the "
        "Pennsieve Discover service. Older SDS files write column names with underscores "
        "(subject_id), newer ones with spaces (subject id); these were treated as the same "
        "column. Old sample column names (specimen type, specimen anatomical location, "
        "wasDerivedFromSample) were matched to the new ones.")
WHY_SUBJECTS = ("SPARC Data Structure paper lists subject_id, species, age, strain and "
                "rrid_for_strain as mandatory subjects fields "
                "(https://www.biorxiv.org/content/10.1101/2021.02.10.430563v2.full; "
                "https://docs.sparc.science/docs/subject-samples-and-identifiers).")
WHY_SAMPLES = ("SPARC Data Structure paper lists subject_id, sample_id and "
               "sample_anatomical_location as mandatory samples fields "
               "(https://www.biorxiv.org/content/10.1101/2021.02.10.430563v2.full; "
               "https://docs.sparc.science/docs/subject-samples-and-identifiers).")


def clean_name(c):
    # "age range (min)" and "age_range_min" are the same column
    c = re.sub(r"[\s_()]+", "_", str(c).strip().lower()).strip("_")
    return OLD_NAMES.get(c, c)


def sparc_datasets(d):
    out, offset = [], 0
    while True:
        page = get_json(URL, params={"limit": 500, "offset": offset},
                        cache=d / f"datasets_{offset}.json")
        out += [x for x in page["datasets"] if x["organizationName"] in ORGS]
        offset += 500
        if offset >= page["totalCount"]:
            return out


def read_sds(path):
    raw = path.read_bytes()
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = z.namelist()
            if "[Content_Types].xml" not in names:
                # Pennsieve sent the file inside a zip (happens when a path is listed twice)
                inner = [n for n in names if n.lower().endswith((".xlsx", ".csv", ".tsv"))]
                raw = z.read(inner[0])
                if not inner[0].lower().endswith(".xlsx"):
                    sep = "\t" if inner[0].lower().endswith(".tsv") else ","
                    return _tidy(read_text_table(raw, sep=sep))
    if raw[:2] == b"PK":
        df = pd.read_excel(io.BytesIO(raw), dtype=str, keep_default_na=False)
    else:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = read_text_table(raw, sep=sep)
    return _tidy(df)


def _tidy(df):
    df.columns = [clean_name(c) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.map(lambda v: "" if v is None else str(v))
    return df[(df != "").any(axis=1)]


def tables():
    d = repo_dir("sparc")
    found = {"subjects": [], "samples": []}
    for ds in sparc_datasets(d):
        listing = get_json(f"{API}/datasets/{ds['id']}/versions/{ds['version']}/files/browse",
                           params={"path": "files", "limit": 500},
                           cache=d / f"browse_{ds['id']}_{ds['version']}.json")
        seen = set()
        for f in listing.get("files", []):
            if f["path"] in seen:  # some listings repeat a file
                continue
            seen.add(f["path"])
            stem, _, ext = f["name"].lower().rpartition(".")
            if stem not in found or ext not in ("xlsx", "csv", "tsv"):
                continue
            dest = d / f"{ds['id']}_{f['name']}"
            path = download_post(API.replace("/discover", "/zipit/discover"), dest,
                                 {"data": {"paths": [f["path"]], "datasetId": ds["id"],
                                           "version": ds["version"]}})
            try:
                df = read_sds(path)
            except Exception as err:  # a few files are broken; report and move on
                print(f"    skipped {dest.name}: {err}")
                continue
            df.insert(0, "dataset", str(ds["id"]))
            found[stem].append(df)

    for stem, cols, spec in (
            ("subjects", SUBJECT_COLS, TableSpec(
                required=["subject_id", "species", "age", "strain", "rrid_for_strain"],
                required_why=WHY_SUBJECTS, keys=[["dataset", "subject_id"]], note=NOTE)),
            ("samples", SAMPLE_COLS, TableSpec(
                required=["subject_id", "sample_id", "sample_anatomical_location"],
                required_why=WHY_SAMPLES, keys=[["dataset", "subject_id", "sample_id"]],
                note=NOTE))):
        frames = found[stem]
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        df = df.reindex(columns=["dataset"] + cols).fillna("")
        yield Table(f"SDS {stem} files ({len(frames)} SPARC datasets)", URL, df=df, spec=spec)

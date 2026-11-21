"""4DN: all released experiment sets, plus a random handful of BED files.

Required fields come from the ExperimentSetReplicate schema
(https://data.4dnucleome.org/profiles/ExperimentSetReplicate.json) and from
the BED format page (https://genome.ucsc.edu/FAQ/FAQformat.html#format1).
"""

import gzip
import random

import pandas as pd

from .. import formats as F
from ..checks import Check, TableSpec
from ..fetch import download, get_json, records_to_table, repo_dir
from ..table import Table

NAME = "4DN"
WHAT = "Repository data"
DATA = ("All released experiment sets, plus 10 random BED files "
        "(7 boundaries, 3 methylation signal) opened row by row.")

SITE = "https://data.4dnucleome.org"
SETS = SITE + "/search/?type=ExperimentSetReplicate&status=released"
BEDS = SITE + "/search/?type=FileProcessed&file_format.file_format=bed"
FIELDS = ["accession", "description", "experimentset_type",
          "experiments_in_set.experiment_type.display_title",
          "experiments_in_set.biosample.biosource_summary", "lab.display_title",
          "public_release", "date_created", "dataset_label", "condition", "award.project"]
# Change the seed (or set BED_FILES) to look at other files.
SEED = 4
BED_FILES = None   # for example {"boundaries": ["4DNFI..."], "methylation signal": [...]}


def _join(items, *path):
    out = []
    for it in items or []:
        for p in path:
            it = (it or {}).get(p)
        if it and it not in out:
            out.append(it)
    return "; ".join(out)


def experiment_sets():
    d = repo_dir("4dn")
    q = SETS + "&format=json&limit=all&" + "&".join(f"field={f}" for f in FIELDS)
    graph = get_json(q, cache=d / "experiment_sets.json")["@graph"]
    rows = []
    for g in graph:
        exps = g.get("experiments_in_set")
        rows.append({"accession": g.get("accession"), "description": g.get("description"),
                     "experimentset_type": g.get("experimentset_type"),
                     "experiment_type": _join(exps, "experiment_type", "display_title"),
                     "biosource": _join(exps, "biosample", "biosource_summary"),
                     "lab": (g.get("lab") or {}).get("display_title"),
                     "public_release": g.get("public_release"),
                     "date_created": g.get("date_created"),
                     "dataset_label": g.get("dataset_label"), "condition": g.get("condition"),
                     "project": (g.get("award") or {}).get("project")})
    return records_to_table(rows)


def pick_bed_files():
    d = repo_dir("4dn")
    q = BEDS + "&status=released&genome_assembly=GRCh38&format=json&limit=all" \
               "&field=accession&field=file_type&field=href&field=open_data_url"
    graph = get_json(q, cache=d / "bed_files.json")["@graph"]
    rng = random.Random(SEED)
    picked = {}
    for ftype, n in (("boundaries", 7), ("methylation signal", 3)):
        pool = sorted((g for g in graph if g.get("file_type") == ftype),
                      key=lambda g: g["accession"])
        if BED_FILES and ftype in BED_FILES:
            pool = [g for g in pool if g["accession"] in BED_FILES[ftype]]
            picked[ftype] = pool
        else:
            picked[ftype] = rng.sample(pool, min(n, len(pool)))
    return picked


def read_bed(files):
    d = repo_dir("4dn")
    parts = []
    for g in files:
        # the portal download link needs a login; the same file is on the 4DN open data bucket
        url = g.get("open_data_url") or SITE + g["href"]
        path = download(url, d / g["href"].split("/")[-1])
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt") as fh:
            rows = [ln.rstrip("\n").split("\t") for ln in fh
                    if ln.strip() and not ln.startswith(("#", "track", "browser"))]
        width = max(len(r) for r in rows)
        names = ["chrom", "start", "end"] + [f"col{i}" for i in range(4, width + 1)]
        df = pd.DataFrame([r + [""] * (width - len(r)) for r in rows], columns=names, dtype=str)
        df.insert(0, "file", g["accession"])
        parts.append(df)
    return pd.concat(parts, ignore_index=True).fillna("")


def start_before_end(df):
    s = pd.to_numeric(df["start"], errors="coerce")
    e = pd.to_numeric(df["end"], errors="coerce")
    bad = int((s >= e).sum())
    return [Check("Standard format", "Wrong format",
                  "Intervals where start is not less than end (BED rule)", len(df), bad)]


def tables():
    df = experiment_sets()
    spec = TableSpec(required=["accession", "project", "lab", "description"],
                     required_why="4DN ExperimentSetReplicate schema requires award, lab and "
                                  "description (https://data.4dnucleome.org/profiles/"
                                  "ExperimentSetReplicate.json); award is shown here by its "
                                  "project; accession is the record ID.",
                     ids=["accession"],
                     formats=[("accession", "4DNES + 7 characters, 4DN accession", F.FOURDN_EXPSET),
                              ("public_release", "YYYY-MM-DD", F.iso_date),
                              ("date_created", "ISO 8601", F.iso_datetime)])
    yield Table("Experiment sets (all released)", SETS, df=df, spec=spec)

    bed_why = ("BED format: chrom, chromStart and chromEnd are the three required fields "
               "(https://genome.ucsc.edu/FAQ/FAQformat.html#format1).")
    for ftype, files in pick_bed_files().items():
        if not files:
            continue
        df = read_bed(files)
        spec = TableSpec(required=["file", "chrom", "start", "end"], required_why=bed_why,
                         keys=[["file", "chrom", "start", "end"]],
                         formats=[("chrom", "chr1 to chr22, chrX, chrY, chrM", F.BED_CHROM),
                                  ("start", "whole number, BED", F.WHOLE_POS),
                                  ("end", "whole number, BED", F.WHOLE_POS)],
                         extra=[start_before_end],
                         note="Files: " + ", ".join(g["accession"] for g in files) + ".")
        yield Table(f"BED files, {ftype} ({len(files)} random files)", BEDS, df=df, spec=spec)

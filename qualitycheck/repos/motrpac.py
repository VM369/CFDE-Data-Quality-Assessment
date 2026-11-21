"""MoTrPAC: rat endurance training data from the MotrpacRatTraining6moData R package.

The package ships its tables as .rda files on GitHub. pyreadr reads them
without needing R.
"""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import download, repo_dir
from ..table import Table

NAME = "MoTrPAC"
WHAT = "Repository data"
DATA = ("Rat phenotypes, RNA-seq sample QC and raw RNA-seq counts for 3 tissues "
        "(MotrpacRatTraining6moData).")
PAGE = "https://github.com/MoTrPAC/MotrpacRatTraining6moData/blob/master/data/"
RAW = "https://raw.githubusercontent.com/MoTrPAC/MotrpacRatTraining6moData/master/data/"
COUNT_TISSUES = ["HEART", "VENACV", "BLOOD"]
KEY_WHY = ("Key fields: the repository does not publish a required-field list, so only the "
           "ID or key needed to use each record is treated as required.")


def read_rda(name):
    import pyreadr  # only this repository needs it
    path = download(RAW + name + ".rda", repo_dir("motrpac") / (name + ".rda"))
    df = list(pyreadr.read_r(str(path)).values())[0]
    return df.reset_index(drop=True)


def as_text(df):
    """Every cell as text, the way R would print it. Missing (NA) becomes empty."""
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map(lambda v: "" if v is None or (isinstance(v, float) and v != v)
                            else str(v))
    return out


def count_lines(df):
    samples = [c for c in df.columns if c not in ("feature", "feature_ID", "tissue", "assay")]
    yield "\t".join(["feature_ID"] + samples)
    for row in df[["feature_ID"] + samples].itertuples(index=False):
        yield "\t".join("" if v is None or v != v else str(v) for v in row)


def tables():
    pheno = as_text(read_rda("PHENO"))
    yield Table("PHENO (rat phenotypes, all samples)", PAGE + "PHENO.rda", df=pheno,
                spec=TableSpec(required=["viallabel", "pid"], required_why=KEY_WHY,
                               ids=["viallabel"],
                               formats=[("pid", "number, MoTrPAC participant ID", F.WHOLE_POS),
                                        ("viallabel", "number, MoTrPAC vial label", F.WHOLE_POS)]))
    meta = as_text(read_rda("TRNSCRPT_META"))
    yield Table("TRNSCRPT_META (RNA-seq sample QC)", PAGE + "TRNSCRPT_META.rda", df=meta,
                spec=TableSpec(required=["vial_label"], required_why=KEY_WHY, ids=["vial_label"]))
    for t in COUNT_TISSUES:
        name = f"TRNSCRPT_{t}_RAW_COUNTS"
        counts = read_rda(name)
        yield Table(f"Raw counts, rat {t.lower()}", PAGE + name + ".rda",
                    matrix=dict(path_or_lines=count_lines(counts),
                                gene_label="ENSRNOG00000000000 (Ensembl rat gene ID)",
                                gene_pattern=F.ENSEMBL_RAT_GENE))

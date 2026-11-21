"""GTEx v11 open access annotations and read counts.

Types and allowed values come from the two GTEx data dictionary files (DD)
that sit next to the data files (DS) in the same folder.
"""

import gzip

import openpyxl

from .. import formats as F
from ..checks import TableSpec
from ..fetch import download, read_text_table, repo_dir
from ..table import Table

NAME = "GTEx"
WHAT = "Repository data"
DATA = ("v11 sample attributes (all samples), subject phenotypes, and read count "
        "matrices for 4 tissues, checked against the GTEx data dictionary.")

META = "https://storage.googleapis.com/adult-gtex/annotations/v11/metadata-files/"
COUNTS = "https://storage.googleapis.com/adult-gtex/bulk-gex/v11/rna-seq/counts-by-tissue/"
TISSUES = ["artery_coronary", "artery_aorta", "artery_tibial", "whole_blood"]
KEY_WHY = ("Key fields: the repository does not publish a required-field list, so only "
           "the ID or key needed to use each record is treated as required. The GTEx "
           "data dictionary does not mark fields as required.")
NOTE = "Allowed values and types taken from the GTEx data dictionary file."


def read_dictionary(path):
    """VARNAME -> (TYPE, allowed values or None). Open access rows only."""
    ws = openpyxl.load_workbook(path, data_only=True).active
    out = {}
    header = None
    for row in ws.iter_rows(values_only=True):
        if row[0] == "VARNAME":
            header = row
            continue
        if header is None or row[0] is None or row[2] != "Open":
            continue
        values = [str(v).strip() for v in row[8:] if v is not None and str(v).strip()]
        allowed = None
        if values:
            # "1=Male" means the file holds 1
            allowed = {v.split("=", 1)[0].strip() if "encoded" in str(row[4]) else v
                       for v in values}
        out[row[0]] = (str(row[4] or ""), allowed)
    return out


def spec_from_dictionary(dd, df, id_col, id_label, id_rx):
    spec = TableSpec(required=[id_col], required_why=KEY_WHY, ids=[id_col], note=NOTE)
    spec.formats.append((id_col, id_label, id_rx))
    for col, (typ, allowed) in dd.items():
        if col not in df.columns:
            continue
        if allowed:
            spec.allowed[col] = (allowed, "GTEx data dictionary")
        if typ.startswith("integer"):
            spec.int_cols.append(col)
        elif typ == "decimal":
            spec.float_cols.append(col)
    return spec


def tables():
    d = repo_dir("gtex")
    sa_dd = read_dictionary(download(META + "GTEx_Analysis_v11_Annotations_SampleAttributesDD.xlsx",
                                     d / "SampleAttributesDD.xlsx"))
    url = META + "GTEx_Analysis_v11_Annotations_SampleAttributesDS.txt"
    df = read_text_table(download(url, d / "SampleAttributesDS.txt"), sep="\t")
    spec = spec_from_dictionary(sa_dd, df, "SAMPID", "GTEX-XXXXX-..., GTEx sample ID",
                                r"GTEX-[0-9A-Z]+-.+")
    yield Table("Sample attributes (v11, all samples)", url, df=df, spec=spec)

    sp_dd = read_dictionary(download(META + "GTEx_Analysis_v11_Annotations_SubjectPhenotypesDD.xlsx",
                                     d / "SubjectPhenotypesDD.xlsx"))
    url = META + "GTEx_Analysis_v11_Annotations_SubjectPhenotypesDS.txt"
    df = read_text_table(download(url, d / "SubjectPhenotypesDS.txt"), sep="\t")
    spec = spec_from_dictionary(sp_dd, df, "SUBJID", "GTEX-XXXXX, GTEx subject ID",
                                r"GTEX-[0-9A-Z]+")
    yield Table("Subject phenotypes (v11, all subjects)", url, df=df, spec=spec)

    for t in TISSUES:
        url = f"{COUNTS}gene_reads_v11_{t}.gct.gz"
        path = download(url, d / f"gene_reads_v11_{t}.gct.gz")
        with gzip.open(path, "rt") as fh:
            # GCT files start with a version line and a size line
            yield Table(f"Read counts, {t.replace('_', ' ')} (v11)", url,
                        matrix=dict(path_or_lines=fh, skip=2,
                                    gene_label="ENSG00000000000.N (Ensembl gene ID)",
                                    gene_pattern=F.ENSEMBL_HUMAN_GENE))

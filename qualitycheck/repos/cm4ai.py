"""CM4AI: BioPlex U2OS protein interaction files from the UVA Dataverse."""

import zipfile

from .. import formats as F
from ..checks import Check, TableSpec
from ..fetch import download, read_text_table, repo_dir
from ..table import Table

NAME = "CM4AI (Functional Genomics)"
WHAT = "Repository data"
DATA = "BioPlex U2OS protein interaction edge list, bait list and gene node attributes."
URL = "https://dataverse.lib.virginia.edu/api/access/datafile/120795"
KEY_WHY = ("Key fields: the repository does not publish a required-field list, so only the "
           "ID or key needed to use each record is treated as required.")


def pair_checks(df):
    a, b = df["GeneID1"], df["GeneID2"]
    seen = set(zip(a, b))
    reverse = sum(1 for x, y in zip(a, b) if x < y and (y, x) in seen)
    return [Check("Duplicates", "Duplicate IDs",
                  "Same protein pair listed twice in reverse order (A-B and B-A)", len(df), reverse,
                  "The network is undirected, so A-B and B-A are the same interaction."),
            Check("Duplicates", "Duplicate IDs", "Protein paired with itself (GeneID1 = GeneID2)",
                  len(df), int((a == b).sum()))]


def tables():
    zp = download(URL, repo_dir("cm4ai") / "u2os_ppi.zip")
    with zipfile.ZipFile(zp) as z:
        def read(end):
            name = next(n for n in z.namelist() if n.endswith(end))
            return read_text_table(z.read(name), sep="\t")
        edges = read("_edgeList.tsv")
        baits = read("_baitList.tsv")
        nodes = read("ppi_gene_node_attributes.tsv")
    yield Table("BioPlex U2OS edge list (protein pairs)", URL, df=edges, spec=TableSpec(
        required=["GeneID1", "GeneID2"], required_why=KEY_WHY, keys=[["GeneID1", "GeneID2"]],
        formats=[("GeneID1", "NCBI Gene ID, digits", F.NCBI_GENE),
                 ("GeneID2", "NCBI Gene ID, digits", F.NCBI_GENE)],
        extra=[pair_checks]))
    yield Table("BioPlex U2OS bait list", URL, df=baits, spec=TableSpec(
        required=["GeneID", "GeneSymbol"], required_why=KEY_WHY, ids=["GeneID"],
        formats=[("GeneID", "NCBI Gene ID, digits", F.NCBI_GENE)]))
    yield Table("PPI gene node attributes", URL, df=nodes, spec=TableSpec(
        required=["name", "represents"], required_why=KEY_WHY, ids=["name"]))

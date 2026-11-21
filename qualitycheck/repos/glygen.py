"""GlyGen: 4 reviewed data files from the current release."""

from .. import formats as F
from ..checks import TableSpec
from ..fetch import download, read_text_table, repo_dir
from ..table import Table

NAME = "GlyGen"
WHAT = "Repository data"
DATA = ("4 reviewed GlyGen data files (glycans, proteins, glycosylation motifs, "
        "UniCarbKB citations).")
BASE = "https://data.glygen.org/ln2data/releases/data/current/reviewed/"
KEY_WHY = ("Key fields: the repository does not publish a required-field list, so only the "
           "ID or key needed to use each record is treated as required.")

# PubMed writes dates as 2013, 2013 May, 2013 May-Jun or 2013 May 15
MON = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
PUBMED_DATE = rf"\d{{4}}( {MON}(-{MON})?( \d{{1,2}})?)?"
# N-glycosylation sequon: N, any amino acid but P, then S or T
SEQUON = r"N[^P][ST]"

FILES = {
    "glycan_masterlist.csv": TableSpec(
        required=["glytoucan_ac"], required_why=KEY_WHY,
        keys=[["glytoucan_ac", "xref_key", "xref_id"]],
        formats=[("glytoucan_ac", "G00000AA, GlyTouCan accession", F.GLYTOUCAN),
                 ("glycan_mass", "number", F.NUMBER),
                 ("base_composition", "GlyTouCan accession", F.GLYTOUCAN),
                 ("composition", "GlyTouCan accession", F.GLYTOUCAN),
                 ("topology", "GlyTouCan accession", F.GLYTOUCAN)]),
    "human_protein_masterlist.csv": TableSpec(
        required=["uniprotkb_canonical_ac"], required_why=KEY_WHY,
        formats=[(c, "UniProt accession with isoform", F.UNIPROT_ISOFORM)
                 for c in ("uniprotkb_canonical_ac", "reviewed_isoforms", "unreviewed_isoforms")]),
    "human_protein_glycosylation_motifs.csv": TableSpec(
        required=["uniprotkb_canonical_ac", "start_pos", "end_pos", "motif"], required_why=KEY_WHY,
        keys=[["uniprotkb_canonical_ac", "start_pos", "end_pos"]],
        formats=[("uniprotkb_canonical_ac", "UniProt accession with isoform", F.UNIPROT_ISOFORM),
                 ("start_pos", "whole number", F.WHOLE_POS),
                 ("end_pos", "whole number", F.WHOLE_POS),
                 ("motif", "N-X-S/T sequon", SEQUON)]),
    "human_proteoform_citations_glycosylation_sites_unicarbkb.csv": TableSpec(
        required=["uniprotkb_canonical_ac", "xref_key", "xref_id"], required_why=KEY_WHY,
        formats=[("uniprotkb_canonical_ac", "UniProt accession with isoform", F.UNIPROT_ISOFORM),
                 ("publication_date", "PubMed style: YYYY, YYYY Mon, YYYY Mon-Mon or YYYY Mon DD",
                  PUBMED_DATE),
                 ("glytoucan_ac", "GlyTouCan accession", F.GLYTOUCAN)]),
}


def tables():
    d = repo_dir("glygen")
    for name, spec in FILES.items():
        df = read_text_table(download(BASE + name, d / name))
        yield Table(name, BASE + name, df=df, spec=spec)

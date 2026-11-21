"""Format rules taken from standards. Each one has the link it came from."""

import re
from datetime import date, datetime

# ISO 8601 (https://www.iso.org/iso-8601-date-and-time-format.html)
YMD = r"\d{4}-\d{2}-\d{2}"


def iso_date(v):
    try:
        date.fromisoformat(v[:10])
    except ValueError:
        return False
    return re.fullmatch(YMD, v[:10]) is not None


# a plain regex, because datetime.fromisoformat accepts more on newer Python
ISO_DT = YMD + r"([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?"


def iso_datetime(v):
    return iso_date(v) and re.fullmatch(ISO_DT, v) is not None


NUMBER = r"[+-]?(\d+(\.\d+)?|\.\d+)([eE][+-]?\d+)?"
WHOLE = r"[+-]?\d+"
WHOLE_POS = r"\d+"
MD5 = r"[0-9a-fA-F]{32}"
SHA256 = r"[0-9a-fA-F]{64}"

# https://www.uniprot.org/help/accession_numbers
UNIPROT = r"([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})"
UNIPROT_ISOFORM = UNIPROT + r"(-\d+)?"
# https://glytoucan.org (accession G + 5 digits + 2 letters)
GLYTOUCAN = r"G\d{5}[A-Z]{2}"
ENSEMBL_HUMAN_GENE = r"ENSG\d{11}(\.\d+)?(_PAR_Y)?"
ENSEMBL_RAT_GENE = r"ENSRNOG\d{11}(\.\d+)?"
MGI = r"MGI:\d+"
DOID = r"DOID:\d+"
NCBI_GENE = r"\d+"

# Ontology term IDs named in the C2M2 schema descriptions
# (https://docs.nih-cfde.org/en/latest/c2m2/draft-C2M2_specification/)
def term(*prefixes):
    return r"(" + "|".join(prefixes) + r"):\d+"


C2M2_TERMS = {
    "anatomy": ("UBERON, CL, CLO term ID", term("UBERON", "CL", "CLO")),
    "biofluid": ("UBERON, InterLex term ID", term("UBERON", "ILX") + r"|ILX:\w+"),
    "sample_prep_method": ("OBI term ID", term("OBI")),
    "assay_type": ("OBI term ID", term("OBI")),
    "analysis_type": ("OBI term ID", term("OBI")),
    "file_format": ("EDAM term ID", r"format:\d+"),
    "compression_format": ("EDAM term ID", r"format:\d+"),
    "data_type": ("EDAM term ID", r"data:\d+"),
}

# 4DN and SMaHT accession formats, from their schemas
FOURDN_EXPSET = r"4DNES[0-9A-Z]{7}"
SMAHT_ACCESSION = r"SMA[A-Z]{2}[0-9A-Z]{7}"

# BED (https://genome.ucsc.edu/FAQ/FAQformat.html#format1). Main human chromosomes.
BED_CHROM = r"chr([1-9]|1\d|2[0-2]|X|Y|M)"

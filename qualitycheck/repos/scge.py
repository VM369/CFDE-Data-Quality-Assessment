"""SCGE: public C2M2 package plus the public toolkit experiment list."""

import re

import pandas as pd
import requests
from lxml import html

from .. import formats as F
from ..c2m2 import load_package
from ..checks import TableSpec
from ..fetch import HEADERS, download, repo_dir
from ..table import Table

NAME = "SCGE"
WHAT = "C2M2 metadata + public list"
DATA = ("C2M2 biosample and subject tables (the file table has 0 rows) and the "
        "public toolkit experiments.")
URL = "https://cfde-drc.s3.amazonaws.com/SCGE/C2M2/2025-10-16/scge_cfde_submission_20251016_143304.zip"
TOOLKIT = "https://scge.mcw.edu/toolkit/data/search/results/Experiment?searchTerm="
NOTE = "C2M2 package (public metadata). Rules taken from the JSON schema inside the same package."


def toolkit_table():
    """The experiment search page lists one experiment per table row."""
    path = repo_dir("scge") / "toolkit_experiments.html"
    if not path.exists():
        r = requests.get(TOOLKIT, headers=HEADERS, timeout=120)
        r.raise_for_status()
        path.write_text(r.text)
    page = html.fromstring(path.read_text())
    out = []
    for tr in page.xpath('//div[@id="listViewContent"]//table/tr'):
        title = " ".join(tr.xpath('.//h4//a/text()')).strip()
        small = [s.text_content() for s in tr.xpath('.//small')]
        kind = next((s.strip(" -\xa0[]") for s in small if "[In " in s), "")
        tags = next((s.strip("[] ") for s in small if s.strip().startswith("[") and "[In " not in s), "")
        pi = " ".join(tr.xpath('.//small/span[not(@class)]/text()')).strip()
        date = re.search(r"Last Updated Date:\s*([^\s<]*)", tr.text_content())
        desc = " ".join(t.strip() for t in tr.xpath('./td/div/span/text()')).strip()
        project = " ".join(tr.xpath('.//details//li/a/text()')).strip()
        out.append({"title": title, "project": project, "experiment type": kind,
                    "category": tags, "lab PI": pi,
                    "last updated": date.group(1) if date else "", "description": desc})
    df = pd.DataFrame(out, dtype=str)
    # the page wraps text over several lines; tidy that up, it is page layout, not data
    return df.apply(lambda col: col.str.replace(r"\s+", " ", regex=True).str.strip())


def tables():
    zp = download(URL, repo_dir("scge") / "c2m2.zip")
    for label, df, spec in load_package(zp, NOTE):
        yield Table(label, URL, df=df, spec=spec)
    df = toolkit_table()
    spec = TableSpec(required=["title", "project"],
                     required_why="Key fields: the repository does not publish a required-field "
                                  "list, so only the ID or key needed to use each record is "
                                  "treated as required.",
                     note="Fields read from each row of the public experiment search page.")
    spec.keys = [spec.required]
    spec.formats.append(("last updated", "YYYY-MM-DD", F.iso_date))
    yield Table("Toolkit experiment list (all public experiments)", TOOLKIT, df=df, spec=spec)

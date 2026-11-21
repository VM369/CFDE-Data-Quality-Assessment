"""A2CPS: public REDCap data dictionaries (participant data is controlled)."""

import requests
from lxml import html

from ..checks import TableSpec
from ..fetch import HEADERS, download, read_text_table, repo_dir
from ..table import Table

NAME = "A2CPS"
WHAT = "Public data dictionary only"
DATA = "The 6 public REDCap data dictionaries. Participant data is controlled."
PAGE = "https://a2cps.org/researchers/data-releases/about-the-data/"


def dictionary_links():
    page = requests.get(PAGE, headers=HEADERS, timeout=60)
    page.raise_for_status()
    links = html.fromstring(page.content).xpath("//a/@href")
    return list(dict.fromkeys(u for u in links if u.lower().endswith(".csv")))


def tables():
    d = repo_dir("a2cps")
    spec = TableSpec(
        required=["field_name", "form_name", "field_type", "field_label"],
        required_why=("REDCap data dictionary: Variable/Field Name, Form Name, Field Type and "
                      "Field Label must be filled in for every row "
                      "(https://atlas.utdallas.edu/TDClient/30/Portal/KB/Article/1142/"
                      "Editing-the-REDCap-Data-Dictionary)."),
        ids=["field_name"],
        note="Public data dictionary (participant data itself is controlled).")
    for url in sorted(dictionary_links(), key=lambda u: u.rsplit("/", 1)[-1]):
        name = url.rsplit("/", 1)[-1]
        df = read_text_table(download(url, d / name))
        yield Table(name, PAGE, df=df, spec=spec)

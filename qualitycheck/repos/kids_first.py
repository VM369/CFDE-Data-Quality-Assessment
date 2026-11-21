"""Kids First: public C2M2 package on the CFDE portal."""

from ..c2m2 import load_package
from ..fetch import download, repo_dir
from ..table import Table

NAME = "Kids First"
WHAT = "C2M2 metadata only"
DATA = "C2M2 biosample, subject and file tables. Participant data is controlled (dbGaP)."
URL = "https://cfde-drc.s3.amazonaws.com/KidsFirst/C2M2/2026-09-16/2026Q4_C2M2_datapackage.zip"
NOTE = "C2M2 package (public metadata). Participant data is controlled (dbGaP). Rules taken from the JSON schema inside the same package."


def tables():
    zp = download(URL, repo_dir("kids_first") / "c2m2.zip")
    for label, df, spec in load_package(zp, NOTE):
        yield Table(label, URL, df=df, spec=spec)

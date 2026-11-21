"""AI-READI (Salutogenesis): public C2M2 package on the CFDE portal."""

from ..c2m2 import load_package
from ..fetch import download, repo_dir
from ..table import Table

NAME = "AI-READI (Salutogenesis)"
WHAT = "C2M2 metadata only"
DATA = "C2M2 biosample, subject and file tables. Participant data is controlled."
URL = "https://cfde-drc.s3.amazonaws.com/Bridge2AI/C2M2/2026-01-08/C2M2_datapackage.zip"
NOTE = "C2M2 package (public metadata). Participant data is controlled. Rules taken from the JSON schema inside the same package."


def tables():
    zp = download(URL, repo_dir("ai_readi") / "c2m2.zip")
    for label, df, spec in load_package(zp, NOTE):
        yield Table(label, URL, df=df, spec=spec)

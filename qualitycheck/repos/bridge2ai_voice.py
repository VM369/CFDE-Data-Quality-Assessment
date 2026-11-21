"""Bridge2AI-Voice (Precision Public Health): public C2M2 package on the CFDE portal."""

from ..c2m2 import load_package
from ..fetch import download, repo_dir
from ..table import Table

NAME = "Bridge2AI-Voice (Precision Public Health)"
WHAT = "C2M2 metadata only"
DATA = "C2M2 biosample, subject and file tables. Voice data is credentialed."
URL = "https://cfde-drc.s3.amazonaws.com/Bridge2AI/C2M2/2026-06-10/bridge2ai_voice_2026_06_C2M2.zip"
NOTE = "C2M2 package (public metadata). Voice data is credentialed. Rules taken from the JSON schema inside the same package."


def tables():
    zp = download(URL, repo_dir("bridge2ai_voice") / "c2m2.zip")
    for label, df, spec in load_package(zp, NOTE):
        yield Table(label, URL, df=df, spec=spec)

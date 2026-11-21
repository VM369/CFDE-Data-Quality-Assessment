"""ExRNA: public C2M2 package on the CFDE portal.

The ExRNA data files gave HTTP 502 errors, so the C2M2 record is what we can check.
"""

from ..c2m2 import load_package
from ..fetch import download, repo_dir
from ..table import Table

NAME = "ExRNA"
WHAT = "C2M2 metadata only"
DATA = "C2M2 biosample, subject and file tables. The data files themselves returned HTTP 502 when we tried them, so only the C2M2 record was checked."
URL = "https://cfde-drc.s3.amazonaws.com/ExRNA/C2M2/2026-08-28/CFDE08272026_C2M2.zip"
NOTE = "C2M2 package (public metadata). Rules taken from the JSON schema inside the same package."


def tables():
    zp = download(URL, repo_dir("exrna") / "c2m2.zip")
    for label, df, spec in load_package(zp, NOTE):
        yield Table(label, URL, df=df, spec=spec)

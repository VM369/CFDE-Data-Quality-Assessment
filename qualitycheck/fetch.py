"""Download helpers. Files are kept in data/<repo>/ so a second run is quick."""

import io
import json
import time
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path("data")
HEADERS = {"User-Agent": "CFDE-Data-Quality-Assessment (University of Arizona)"}


def repo_dir(repo):
    d = DATA_DIR / repo
    d.mkdir(parents=True, exist_ok=True)
    return d


def download(url, dest, tries=3):
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    for i in range(tries):
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
            tmp.rename(dest)
            return dest
        except requests.RequestException as err:
            if i == tries - 1:
                raise RuntimeError(f"could not download {url}: {err}") from err
            time.sleep(5 * (i + 1))


def get_json(url, params=None, cache=None, method="GET", body=None):
    if cache and Path(cache).exists():
        return json.loads(Path(cache).read_text())
    for i in range(3):
        try:
            if method == "POST":
                r = requests.post(url, json=body, headers=HEADERS, timeout=120)
            else:
                r = requests.get(url, params=params, headers=HEADERS, timeout=120)
            r.raise_for_status()
            data = r.json()
            break
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(5 * (i + 1))
    if cache:
        Path(cache).write_text(json.dumps(data))
    return data


def read_text_table(src, sep=",", skiprows=0, **kw):
    """Read a CSV or TSV with every cell kept as text, exactly as written."""
    if isinstance(src, (bytes, bytearray)):
        src = io.BytesIO(src)
    return pd.read_csv(src, sep=sep, dtype=str, keep_default_na=False,
                       skiprows=skiprows, low_memory=False, **kw)


def records_to_table(records, columns=None):
    """List of dicts from an API into a text table. None becomes an empty cell."""
    df = pd.DataFrame.from_records(records, columns=columns)
    for c in df.columns:
        df[c] = df[c].map(lambda v: "" if v is None or (isinstance(v, float) and v != v)
                          else ("; ".join(map(str, v)) if isinstance(v, list) else str(v)))
    return df


def download_post(url, dest, body, tries=3):
    """Same as download() but for services that hand out a file in reply to a POST."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for i in range(tries):
        try:
            r = requests.post(url, json=body, headers=HEADERS, timeout=120)
            r.raise_for_status()
            dest.write_bytes(r.content)
            return dest
        except requests.RequestException as err:
            if i == tries - 1:
                raise RuntimeError(f"could not download {url}: {err}") from err
            time.sleep(5 * (i + 1))

"""C2M2 packages (biosample, subject and file tables).

Rules come from the JSON schema shipped inside each package
(C2M2_datapackage.json), so every program is checked against the version of
C2M2 it submitted with. Spec: https://docs.nih-cfde.org/en/latest/c2m2/draft-C2M2_specification/
"""

import json
import zipfile

from . import formats as F
from .checks import Check, TableSpec, missing_masks
from .fetch import read_text_table

C2M2_SPEC = "https://docs.nih-cfde.org/en/latest/c2m2/draft-C2M2_specification/"
TABLES = [("biosample", "C2M2 biosample table"),
          ("subject", "C2M2 subject table"),
          ("file", "C2M2 file table")]


def _member(z, name):
    for n in z.namelist():
        if n.split("/")[-1] == name:
            return n
    return None


def checksum_check(df):
    """C2M2: sha256 and md5 cannot both be null."""
    if "sha256" not in df.columns and "md5" not in df.columns:
        return []
    none = None
    for c in ("sha256", "md5"):
        if c in df.columns:
            e, h = missing_masks(df[c].astype(str))
            m = e | h
            none = m if none is None else (none & m)
    return [Check("Missing values", "Missing required",
                  "Files with neither SHA-256 nor MD5 (C2M2 schema: they cannot both be null)",
                  len(df), int(none.sum()),
                  "Counted as a required field: the C2M2 schema says sha256 and md5 cannot both be empty.")]


def spec_from_schema(fields, primary_key, note):
    spec = TableSpec(required_why="C2M2 JSON schema marks these fields required "
                                  "(constraints.required = true).", note=note)
    for f in fields:
        name, cons = f["name"], f.get("constraints") or {}
        if cons.get("required"):
            spec.required.append(name)
        if "enum" in cons:
            spec.allowed[name] = (set(cons["enum"]), "C2M2 schema enum")
        typ = f.get("type")
        if typ == "datetime":
            spec.formats.append((name, "ISO 8601 date/time (C2M2 schema type datetime)", F.iso_datetime))
        elif typ == "integer":
            spec.formats.append((name, "whole number (C2M2 schema type integer)", F.WHOLE))
        elif typ == "number":
            spec.formats.append((name, "number (C2M2 schema type number)", F.NUMBER))
        if name == "sha256":
            spec.formats.append((name, "SHA-256, 64 hex characters", F.SHA256))
        if name == "md5":
            spec.formats.append((name, "MD5, 32 hex characters", F.MD5))
        if "pattern" in cons:
            spec.formats.append((name, f"C2M2 schema pattern {cons['pattern']}",
                                 cons["pattern"].strip("^$")))
        if name in F.C2M2_TERMS:
            label, rx = F.C2M2_TERMS[name]
            spec.formats.append((name, f"{label} (C2M2 schema description)", rx))
    spec.ids = ["local_id"]
    spec.keys = [list(primary_key)] if primary_key else []
    return spec


def load_package(zip_path, note):
    """Yield (table name, DataFrame, TableSpec) for biosample, subject, file."""
    with zipfile.ZipFile(zip_path) as z:
        dp_name = next(n for n in z.namelist() if n.endswith("datapackage.json"))
        dp = json.loads(z.read(dp_name))
        schemas = {r["name"]: r["schema"] for r in dp["resources"]}
        for name, label in TABLES:
            member = _member(z, f"{name}.tsv")
            if member is None:
                continue
            sch = schemas[name]
            df = read_text_table(z.read(member), sep="\t")
            spec = spec_from_schema(sch["fields"], sch.get("primaryKey"), note)
            if name == "file":
                spec.extra.append(checksum_check)
            if len(df) == 0:
                spec.note = ("The table has 0 rows. " + note).strip()
            yield label, df, spec

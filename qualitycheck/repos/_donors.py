"""Shared code for HuBMAP and SenNet donor records.

Both portals store donor facts as a list of coded entries under
metadata.organ_donor_data or metadata.living_donor_data. Each entry has a
grouping term (Age, Sex, Race, ...), a value and sometimes a unit.
"""

from .. import formats as F
from ..fetch import records_to_table

FIELDS = ["Age", "Sex", "Race", "Ethnicity", "Body Mass Index", "Height", "Weight",
          "Cause of Death"]
WITH_UNITS = ["Age", "Height", "Weight"]
NUMERIC = ["Age", "Body Mass Index", "Height", "Weight"]
COLUMNS = ["id", "group", "Age", "Age units", "Sex", "Race", "Ethnicity", "Body Mass Index",
           "Height", "Height units", "Weight", "Weight units", "Cause of Death"]


def donor_row(donor_id, group, metadata):
    entries = (metadata or {}).get("organ_donor_data") or (metadata or {}).get("living_donor_data") or []
    vals, units = {}, {}
    for e in entries:
        term = e.get("grouping_concept_preferred_term")
        if term in FIELDS:
            vals.setdefault(term, []).append(str(e.get("data_value", "")).strip())
            if e.get("units"):
                units.setdefault(term, set()).add(e["units"])
    row = {"id": donor_id, "group": group}
    for f in FIELDS:
        row[f] = "; ".join(v for v in dict.fromkeys(vals.get(f, [])) if v)
        if f in WITH_UNITS:
            row[f + " units"] = "; ".join(sorted(units.get(f, [])))
    return row


def donor_table(rows):
    return records_to_table(rows, columns=COLUMNS)


def number_formats():
    return [(c, "number", F.NUMBER) for c in NUMERIC]

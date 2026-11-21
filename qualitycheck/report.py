"""Build the Excel workbook from results/*.json.

Sheets: Summary, Missing values, Checks, Columns, Method, Sources.
Problem % and Result in Checks are Excel formulas that read the yellow limit
cells on the Method sheet, so a reader can change a limit and see every
result update without running the code again.
"""

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .limits import load_limits
from .run import REPOS

STANDARDS = [
    ("UK Government Data Quality Framework (completeness, uniqueness, validity)",
     "https://www.gov.uk/government/publications/the-government-data-quality-framework/"
     "the-government-data-quality-framework"),
    ("ISO/IEC 25012 data quality model", "https://iso25000.com/en/iso-25000-standards/iso-25012"),
    ("CFDE C2M2 specification (the JSON schema inside each package was used for the rules)",
     "https://docs.nih-cfde.org/en/latest/c2m2/draft-C2M2_specification/"),
    ("RO-Crate 1.1 root data entity (datePublished in ISO 8601)",
     "https://www.researchobject.org/ro-crate/specification/1.1/root-data-entity.html"),
    ("GTEx v11 data dictionaries (allowed values and types)",
     "https://storage.googleapis.com/adult-gtex/annotations/v11/metadata-files/"),
    ("BED format (UCSC)", "https://genome.ucsc.edu/FAQ/FAQformat.html#format1"),
    ("UniProt accession format", "https://www.uniprot.org/help/accession_numbers"),
    ("ISO 8601 dates and times", "https://www.iso.org/iso-8601-date-and-time-format.html"),
]

STEPS = [
    "1. Download real data tables from each repository (links on the Sources sheet). Where the "
    "data is controlled, the public metadata tables or public dictionaries are checked instead. "
    "The Summary says which.",
    "2. Read every row and every cell of each table as text, so nothing is changed on loading.",
    "3. Missing values: each column is marked Required or Optional (Columns sheet). Required "
    "comes from the repository's own schema or documentation where one exists. Where none "
    "exists, only the ID or key fields are required. A missing value is an empty cell or hidden "
    "missing text (NA, n/a, null, none, -, --, ?, missing, not available, or codes -999, -9999, 99999). Required "
    "and optional fields are counted separately. See the Missing values sheet.",
    "4. Duplicates: rows that are exact copies of another row, repeated IDs, and repeated keys "
    "(for example the same subject twice in the same dataset). The key is written in the check "
    "name.",
    "5. Standard format: text in columns that are at least 90% numbers, the same label written "
    "different ways (case, spaces, underscores; free-text and ID columns skipped), values with "
    "extra spaces at the start or end, values that break a format rule, and values not in an "
    "allowed list.",
    "6. Format rules and allowed lists come only from a standard or the repository's own "
    "documentation. The rule and its source are written in each check row.",
    "7. Each check row has Records checked and Problems found. Problem % = Problems / Records. "
    "The result comes from the limits below. Summary shows the worst result in each of the "
    "three areas.",
    "8. Every number is a plain count from the downloaded file. Nothing is estimated. Where only "
    "part of a repository is read, the table name says so.",
    "9. Not checked: outliers or statistics on the values, and data behind controlled access "
    "(dbGaP, data use agreements, credentialed access).",
]

HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
YELLOW = PatternFill("solid", fgColor="FFF2CC")
TITLE = Font(bold=True, size=14)
WRAP = Alignment(wrap_text=True, vertical="top")
RESULT_FILL = {"Pass": "E2EFDA", "Check": "FFF2CC", "Fail": "F8CBAD"}


def _load(results_dir):
    res = {}
    for p in sorted(Path(results_dir).glob("*.json")):
        r = json.loads(p.read_text())
        res[r["key"]] = r
    order = [k for k in REPOS if k in res] + [k for k in res if k not in REPOS]
    return [res[k] for k in order]


def _sheet(wb, name, title, note, header, widths):
    ws = wb.create_sheet(name)
    ws["A1"] = title
    ws["A1"].font = TITLE
    ws["A2"] = note
    for i, h in enumerate(header, 1):
        c = ws.cell(4, i, h)
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, WRAP
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return ws


def _findings(r):
    if r.get("not_tested"):
        return "Not tested: no public data to download."
    bad = [(t["table"], c) for t in r["tables"] for c in t["checks"]
           if c["result"] in ("Fail", "Check") and c["rule"] not in ("Empty columns",
                                                                     "Half-empty columns",
                                                                     "Missing optional")]
    if not bad:
        return "Clean. No problems in required fields, duplicates or format checks."
    bad.sort(key=lambda x: (x[1]["result"] != "Fail", -x[1]["problems"]))
    parts = [f"{c['check']}: {c['problems']:,} of {c['records']:,} ({tbl})" for tbl, c in bad[:3]]
    more = f" Plus {len(bad) - 3} more." if len(bad) > 3 else ""
    return "; ".join(parts) + "." + more


def build(results_dir, out):
    results = _load(results_dir)
    if not results:
        raise SystemExit(f"no results in {results_dir}. Run: python -m qualitycheck run all")
    limits = load_limits()
    rules = list(limits["rules"])
    wb = Workbook()
    wb.remove(wb.active)

    # sizes first, so formulas can use fixed ranges
    n_checks = sum(len(t["checks"]) for r in results for t in r.get("tables", []))
    n_tables = sum(len(r.get("tables", [])) for r in results)
    ck_last = 4 + max(n_checks, 1)
    mv_last = 4 + max(n_tables, 1)
    lim_first, lim_last = 17, 16 + len(rules)
    w_req, w_opt = lim_last + 8, lim_last + 9

    def ck(col):
        return f"Checks!${col}$5:${col}${ck_last}"

    def mv(col):
        return f"'Missing values'!${col}$5:${col}${mv_last}"

    # Summary
    ws = _sheet(wb, "Summary", f"CFDE Data Quality Assessment, {len(results)} repositories",
                "Missing values, duplicates, and standard format problems, counted on real "
                "downloaded data.",
                ["Repository", "What was checked", "Data checked", "Tables", "Rows checked",
                 "Missing values", "Required missing %", "Optional missing %",
                 "Missing values score", "Duplicates", "Standard format", "Checks run",
                 "Checks not Pass", "Main findings (plain counts)"],
                [24, 16, 42, 8, 12, 11, 11, 11, 10, 11, 11, 8, 9, 70])
    for i, r in enumerate(results, 5):
        tables = r.get("tables", [])
        ws.cell(i, 1, r["repository"])
        ws.cell(i, 2, r["what"])
        ws.cell(i, 3, r["data"])
        ws.cell(i, 4, len(tables))
        ws.cell(i, 5, sum(t["rows"] for t in tables))
        for col, area in ((6, "Missing values"), (10, "Duplicates"), (11, "Standard format")):
            cnt = [f'COUNTIFS({ck("A")},$A{i},{ck("C")},"{area}",{ck("K")},"{x}")>0'
                   for x in ("Fail", "Check", "Pass")]
            ws.cell(i, col, f'=IF(COUNTIF({ck("A")},$A{i})=0,"Not tested",'
                            f'IF({cnt[0]},"Fail",IF({cnt[1]},"Check",IF({cnt[2]},"Pass",'
                            f'"No records"))))')
        ws.cell(i, 7, f'=IF(SUMIFS({mv("E")},{mv("A")},$A{i})=0,"",'
                      f'SUMIFS({mv("F")},{mv("A")},$A{i})/SUMIFS({mv("E")},{mv("A")},$A{i}))')
        ws.cell(i, 8, f'=IF(SUMIFS({mv("H")},{mv("A")},$A{i})=0,"",'
                      f'SUMIFS({mv("I")},{mv("A")},$A{i})/SUMIFS({mv("H")},{mv("A")},$A{i}))')
        ws.cell(i, 9, f'=IF(G{i}="","",IF(H{i}="",100*(1-G{i}),100*(Method!$B${w_req}*(1-G{i})'
                      f'+Method!$B${w_opt}*(1-H{i}))/(Method!$B${w_req}+Method!$B${w_opt})))')
        ws.cell(i, 12, f'=COUNTIF({ck("A")},$A{i})')
        ws.cell(i, 13, f'=COUNTIFS({ck("A")},$A{i},{ck("K")},"Check")'
                       f'+COUNTIFS({ck("A")},$A{i},{ck("K")},"Fail")')
        ws.cell(i, 14, _findings(r))
        for c in (7, 8):
            ws.cell(i, c).number_format = "0.00%"
        ws.cell(i, 9).number_format = "0.0"
        for c in (3, 14):
            ws.cell(i, c).alignment = WRAP
    last = 5 + len(results)
    ws.cell(last + 1, 1, "Public metadata only, C2M2 metadata only or Public data dictionary "
                         "only: the data itself is controlled, so the repository's public record "
                         "of its data was checked instead.")
    ws.cell(last + 2, 1, "This workbook is separate from the evaluation matrix. It adds no "
                         "criterion and no score to the matrix.")
    ws.freeze_panes = "B5"

    # Missing values
    ws = _sheet(wb, "Missing values", "Missing values: required vs optional fields",
                "One row per table. Required cells = rows x required columns (plus any extra "
                "required rule). A missing value is an empty cell or hidden missing text.",
                ["Repository", "Table", "Required fields", "Why required (source)",
                 "Required cells", "Required missing", "Required missing %", "Optional cells",
                 "Optional missing", "Optional missing %", "Missing values score"],
                [22, 30, 30, 60, 13, 12, 11, 13, 12, 11, 11])
    i = 5
    for r in results:
        for t in r.get("tables", []):
            m = t["missing"]
            ws.cell(i, 1, r["repository"])
            ws.cell(i, 2, t["table"])
            ws.cell(i, 3, m.get("required_fields", ""))
            ws.cell(i, 4, m.get("required_why", ""))
            for col, src, rule in ((5, "E", "Missing required"), (6, "F", "Missing required"),
                                   (8, "E", "Missing optional"), (9, "F", "Missing optional")):
                ws.cell(i, col, f'=SUMIFS({ck(src)},{ck("A")},$A{i},{ck("B")},$B{i},'
                                f'{ck("H")},"{rule}")')
            ws.cell(i, 7, f'=IF(E{i}=0,"",F{i}/E{i})')
            ws.cell(i, 10, f'=IF(H{i}=0,"",I{i}/H{i})')
            ws.cell(i, 11, f'=IF(E{i}=0,"",IF(H{i}=0,100*(1-G{i}),100*(Method!$B${w_req}'
                           f'*(1-G{i})+Method!$B${w_opt}*(1-J{i}))/(Method!$B${w_req}'
                           f'+Method!$B${w_opt})))')
            for c in (7, 10):
                ws.cell(i, c).number_format = "0.00%"
            ws.cell(i, 11).number_format = "0.0"
            ws.cell(i, 4).alignment = WRAP
            i += 1
    ws.freeze_panes = "C5"

    # Checks
    ws = _sheet(wb, "Checks", "Checks",
                "One row per check on one real table. Problem % and Result are formulas that "
                "use the limits on the Method sheet.",
                ["Repository", "Table", "Area", "Check", "Records checked", "Problems found",
                 "Problem %", "Rule", "Pass limit", "Fail limit", "Result", "Details",
                 "Source URL"],
                [22, 30, 15, 60, 12, 12, 10, 18, 9, 9, 10, 70, 50])
    lim_a = f"Method!$A${lim_first}:$A${lim_last}"
    i = 5
    for r in results:
        for t in r.get("tables", []):
            for c in t["checks"]:
                vals = [r["repository"], t["table"], c["area"], c["check"], c["records"],
                        c["problems"], f"=IF(E{i}=0,0,F{i}/E{i})", c["rule"],
                        f"=INDEX(Method!$C${lim_first}:$C${lim_last},MATCH(H{i},{lim_a},0))",
                        f"=INDEX(Method!$D${lim_first}:$D${lim_last},MATCH(H{i},{lim_a},0))",
                        f'=IF(E{i}=0,"No records",IF(G{i}<=I{i}+0.000000000001,"Pass",'
                        f'IF(G{i}>J{i}+0.000000000001,"Fail","Check")))',
                        c["details"], t["source"]]
                for col, v in enumerate(vals, 1):
                    ws.cell(i, col, v)
                ws.cell(i, 7).number_format = "0.00%"
                for col in (9, 10):
                    ws.cell(i, col).number_format = "0%"
                ws.cell(i, 12).alignment = WRAP
                fill = RESULT_FILL.get(c["result"])
                if fill:
                    ws.cell(i, 11).fill = PatternFill("solid", fgColor=fill)
                i += 1
    ws.freeze_panes = "E5"
    ws.auto_filter.ref = f"A4:M{max(i - 1, 4)}"

    # Columns
    ws = _sheet(wb, "Columns", "Columns",
                "One row per column of every table checked. Counts are from the downloaded "
                "files.",
                ["Repository", "Table", "Column", "Required?", "Kind", "Rows", "Empty cells",
                 "Empty %", "Hidden missing", "Unique values", "Example value"],
                [20, 30, 30, 10, 13, 11, 11, 9, 11, 11, 40])
    i = 5
    for r in results:
        for t in r.get("tables", []):
            for col in t["columns"]:
                vals = [r["repository"], t["table"], col["column"],
                        "Yes" if col["required"] else "No", col["kind"], col["rows"],
                        col["empty"], f"=IF(F{i}=0,0,G{i}/F{i})", col["hidden"], col["unique"],
                        str(col.get("example") or "")[:60]]
                for c, v in enumerate(vals, 1):
                    ws.cell(i, c, v)
                ws.cell(i, 8).number_format = "0.0%"
                i += 1
    ws.freeze_panes = "D5"

    # Method
    ws = wb.create_sheet("Method")
    ws["A1"] = "Method"
    ws["A1"].font = TITLE
    ws["A2"] = ("What was counted and how a result is given. Change a yellow limit and every "
                "result in Checks and Summary updates.")
    ws["A4"] = "Steps"
    ws["A4"].font = Font(bold=True)
    for k, s in enumerate(STEPS, 5):
        ws.cell(k, 1, s)
    ws.cell(lim_first - 2, 1, "Limits (working numbers, editable)").font = Font(bold=True)
    for c, h in enumerate(["Rule", "Area", "Pass if problem % is at most",
                           "Fail if problem % is above", "Why this limit"], 1):
        cell = ws.cell(lim_first - 1, c, h)
        cell.font, cell.fill, cell.alignment = HEAD, HEAD_FILL, WRAP
    for k, name in enumerate(rules, lim_first):
        lim = limits["rules"][name]
        ws.cell(k, 1, name)
        ws.cell(k, 2, lim["area"])
        for c, key in ((3, "pass"), (4, "fail")):
            cell = ws.cell(k, c, lim[key])
            cell.fill = YELLOW
            cell.number_format = "0%"
        ws.cell(k, 5, lim["why"])
    ws.cell(lim_last + 2, 1, 'Result rule: "No records" if the table has 0 records. "Pass" if '
                             'problem % is at most the Pass limit. "Fail" if above the Fail '
                             'limit. Otherwise "Check".')
    ws.cell(lim_last + 3, 1, "Area result on Summary: Fail if any check in that area fails, "
                             "else Check if any check is Check, else Pass.")
    ws.cell(lim_last + 4, 1, "The limits are working numbers for this review, not a published "
                             "standard.")
    ws.cell(w_req - 2, 1, "Missing values score (working numbers, editable)").font = Font(bold=True)
    for c, h in enumerate(["Weight", "Value", "Meaning"], 1):
        cell = ws.cell(w_req - 1, c, h)
        cell.font, cell.fill = HEAD, HEAD_FILL
    w = limits["score_weights"]
    for row, label, key, meaning in (
            (w_req, "Required fields", "required", "How much filled required fields count."),
            (w_opt, "Optional fields", "optional", "How much filled optional fields count.")):
        ws.cell(row, 1, label)
        ws.cell(row, 2, w[key]).fill = YELLOW
        ws.cell(row, 3, meaning)
    ws.cell(w_opt + 1, 1, "Missing values score = 100 x (Required weight x share of required "
                          "cells filled + Optional weight x share of optional cells filled) / "
                          "(Required weight + Optional weight). If there are no optional cells, "
                          "only the required part is used.")
    ws.cell(w_opt + 2, 1, "Example: 0.5% of required cells missing and 40% of optional cells "
                          "missing gives 100 x (0.8 x 0.995 + 0.2 x 0.60) / 1.0 = 91.6.")
    for col, wdt in zip("ABCDE", (20, 18, 16, 16, 70)):
        ws.column_dimensions[col].width = wdt

    # Sources
    ws = _sheet(wb, "Sources", "Sources",
                "Where each table was downloaded from, and the standards used for the rules.",
                ["Repository", "Table", "URL"], [24, 50, 100])
    i = 5
    for r in results:
        for s in r.get("sources", []):
            ws.cell(i, 1, r["repository"])
            ws.cell(i, 2, s["table"])
            ws.cell(i, 3, s["url"])
            i += 1
    i += 1
    ws.cell(i, 1, "Standards and rule sources").font = Font(bold=True)
    for name, url in STANDARDS:
        i += 1
        ws.cell(i, 1, "Standard")
        ws.cell(i, 2, name)
        ws.cell(i, 3, url)

    # fixed document properties so the file does not carry a run date or user name
    fixed = datetime(2000, 1, 1)
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    wb.properties.created = fixed
    wb.properties.modified = fixed

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    _fix_dates(out)
    return out


def _fix_dates(path):
    """openpyxl writes the save time into docProps/core.xml; put the fixed date back."""
    with zipfile.ZipFile(path) as z:
        parts = [(i, z.read(i.filename)) for i in z.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in parts:
            if info.filename == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(created|modified)[^>]*>)[^<]*",
                              rb"\g<1>2000-01-01T00:00:00Z", data)
            info.date_time = (2000, 1, 1, 0, 0, 0)
            z.writestr(info, data)

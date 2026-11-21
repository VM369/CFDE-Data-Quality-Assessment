"""Counts for missing values, duplicates and standard format on one table.

A table comes in as a pandas DataFrame where every cell is text (read with
dtype=str and keep_default_na=False). Nothing is converted on loading, so the
counts show the file exactly as the repository published it.
"""

import re
from dataclasses import dataclass, field

import pandas as pd

from .limits import result_for

# Text that people type when they mean "no value". Compared after strip + lower.
HIDDEN_MISSING = {"na", "n/a", "nan", "null", "none", "-", "--", "?", "missing",
                  "not available", "-999", "-9999", "99999"}

# Column names that hold free text. Label variant counts skip these.
FREE_TEXT_WORDS = ("comment", "note", "description", "title", "remark", "summary")

NUMBER = re.compile(r"^[+-]?(\d+(\.\d+)?|\.\d+)([eE][+-]?\d+)?$")


def _n(k, word):
    return f"{k} {word}" if k == 1 else f"{k} {word}s"


@dataclass
class Check:
    area: str          # Missing values, Duplicates, Standard format
    rule: str          # key into the limits table, e.g. "Missing required"
    name: str          # what a reader sees in the Checks sheet
    records: int
    problems: int
    details: str = ""

    @property
    def pct(self):
        return self.problems / self.records if self.records else 0.0

    def as_dict(self, limits):
        return {"area": self.area, "rule": self.rule, "check": self.name,
                "records": int(self.records), "problems": int(self.problems),
                "problem_pct": self.pct,
                "result": result_for(self.rule, self.records, self.pct, limits),
                "details": self.details}


@dataclass
class TableSpec:
    """What we know about a table from its standard or its repository.

    required     columns the standard says must be filled
    required_why one sentence with the source of the required list
    ids          columns that should hold a different value on every row
    keys         groups of columns that together should be unique
    formats      list of (column, label, test). test is a regex string or a
                 function taking a value and returning True when it is fine
    allowed      {column: (set of allowed values, where the list comes from)}
    int_cols     columns the dictionary says are whole numbers
    float_cols   columns the dictionary says are decimals
    extra        functions f(df) -> list of Check, for rules that need more
                 than one column (for example BED start < end)
    note         text added to every check row of the table
    """
    required: list = field(default_factory=list)
    required_why: str = ""
    ids: list = field(default_factory=list)
    keys: list = field(default_factory=list)
    formats: list = field(default_factory=list)
    allowed: dict = field(default_factory=dict)
    int_cols: list = field(default_factory=list)
    float_cols: list = field(default_factory=list)
    extra: list = field(default_factory=list)
    note: str = ""


def missing_masks(s):
    t = s.str.strip()
    empty = t.eq("")
    hidden = t.str.lower().isin(HIDDEN_MISSING)
    return empty, hidden


def _is_float(v):
    try:
        f = float(v)
    except ValueError:
        return False
    return f == f and f not in (float("inf"), float("-inf"))


def number_share(values):
    """Share of the filled values in a column that read as numbers."""
    if len(values) == 0:
        return 0.0
    return values.map(_is_float).mean()


def _example(col, vals):
    """One short value to show what the column holds. Free text and emails are left out."""
    if len(vals) == 0:
        return ""
    v = vals.iloc[0].strip()
    if "@" in v or len(v) > 40 or len(v.split()) > 3:
        return ""
    return v


def _skip_for_labels(col, values):
    """Free text and ID columns are not labels, so label variants skip them."""
    n = len(values)
    if n >= 100 and values.nunique() > 0.5 * n:
        return True
    low = col.lower()
    if any(w in low for w in FREE_TEXT_WORDS):
        return True
    return len(values) > 0 and values.str.len().mean() > 40


def label_variants(values):
    """Cells whose label is also written another way in the same column.

    "Plasma", "plasma" and "plasma " count as one label written 3 ways. The
    most common spelling is taken as the main one and the other cells count.
    """
    counts = values.value_counts()
    if counts.empty:
        return 0, []
    norm = pd.Series(counts.index, index=counts.index).str.strip().str.lower()
    norm = norm.str.replace(r"[\s_]+", " ", regex=True)
    bad, examples = 0, []
    for _, grp in counts.groupby(norm.values):
        if len(grp) > 1:
            grp = grp.sort_values(ascending=False)
            bad += int(grp.iloc[1:].sum())
            if len(examples) < 3:
                examples.append(" / ".join(f'"{v}"' for v in grp.index[:3]))
    return bad, examples


def _passes(test, v):
    if callable(test):
        return test(v)
    return re.fullmatch(test, v) is not None


def profile(df, spec, table_name=""):
    """Run every check on one table. Returns (checks, columns, missing_row)."""
    df = df.fillna("")
    rows, cols = df.shape
    note = spec.note
    checks, columns = [], []

    def add(area, rule, name, records, problems, details=""):
        text = " ".join(x for x in (note, details) if x)
        checks.append(Check(area, rule, name, records, problems, text))

    if rows == 0:
        if spec.required:
            add("Missing values", "Missing required",
                f"Missing values in required fields ({_n(len(spec.required), 'column')}: "
                f"{', '.join(spec.required)})", 0, 0)
        return checks, [], {"required_fields": ", ".join(spec.required),
                            "required_why": spec.required_why, "required_cells": 0,
                            "required_missing": 0, "optional_cells": 0, "optional_missing": 0}

    empty_cells = hidden_cells = 0
    empty_cols = half_cols = 0
    filled = {}
    hidden_seen = {}
    for c in df.columns:
        s = df[c].astype(str)
        e, h = missing_masks(s)
        miss = e | h
        empty_cells += int(e.sum())
        hidden_cells += int(h.sum())
        if rows and miss.all():
            empty_cols += 1
        elif rows and miss.mean() > 0.5:
            half_cols += 1
        vals = s[~miss]
        filled[c] = vals
        for v in s[h].str.strip():
            hidden_seen[v] = hidden_seen.get(v, 0) + 1
        share = number_share(vals) if len(vals) else 0.0
        kind = "empty" if len(vals) == 0 else ("number" if share >= 0.9 else "text")
        columns.append({"column": c, "required": c in spec.required, "kind": kind,
                        "rows": rows, "empty": int(e.sum()),
                        "empty_pct": (int(e.sum()) / rows) if rows else 0.0,
                        "hidden": int(h.sum()), "unique": int(vals.nunique()),
                        "example": _example(c, vals)})

    # Missing values, required against optional
    req = [c for c in spec.required if c in df.columns]
    absent = [c for c in spec.required if c not in df.columns]
    opt = [c for c in df.columns if c not in req]
    req_cells = rows * len(spec.required)
    req_miss = sum(rows - len(filled[c]) for c in req) + rows * len(absent)
    opt_cells = rows * len(opt)
    opt_miss = sum(rows - len(filled[c]) for c in opt)
    where = "; ".join(f"{c} ({rows - len(filled[c])})" for c in req
                      if rows - len(filled[c]))
    if absent:
        where = "; ".join(x for x in (where, "column not in file: " + ", ".join(absent)) if x)
    if spec.required:
        add("Missing values", "Missing required",
            f"Missing values in required fields ({_n(len(spec.required), 'column')}: "
            f"{', '.join(spec.required)})", req_cells, req_miss,
            " ".join(x for x in ("Required because: " + spec.required_why
                                 if spec.required_why else "",
                                 "Missing in: " + where if where else "") if x))
    if opt:
        add("Missing values", "Missing optional",
            f"Missing values in optional fields ({_n(len(opt), 'column')})", opt_cells, opt_miss,
            "Empty cells plus hidden missing text (NA, None, -999 and so on).")
    top = sorted(hidden_seen.items(), key=lambda kv: -kv[1])[:3]
    add("Missing values", "Hidden missing",
        "Hidden missing values (text like NA, null, -, or codes like -999)",
        rows * cols, hidden_cells,
        ("Most common: " + ", ".join(f'"{k}" x{v:,}' for k, v in top)) if top else "")
    add("Missing values", "Empty columns", "Columns that are completely empty", cols, empty_cols)
    add("Missing values", "Half-empty columns", "Columns more than half empty", cols, half_cols)

    # Duplicates
    add("Duplicates", "Duplicate rows", "Rows that are exact copies of another row",
        rows, int(df.duplicated().sum()) if rows else 0)
    for c in spec.ids:
        if c in df.columns:
            v = filled[c]
            add("Duplicates", "Duplicate IDs", f'Repeated IDs in "{c}"', rows,
                int(v.duplicated().sum()))
    for key in spec.keys:
        key = [k for k in key if k in df.columns]
        if key:
            add("Duplicates", "Duplicate IDs", f"Repeated records (same {', '.join(key)})",
                rows, int(df.duplicated(subset=key).sum()) if rows else 0)

    # Standard format
    num_records = num_bad = 0
    lv_records = lv_bad = 0
    lv_examples = []
    sp_records = sp_bad = 0
    for c in df.columns:
        vals = filled[c]
        if len(vals) == 0:
            continue
        is_num = vals.map(_is_float)
        share = is_num.mean()
        if share >= 0.9:
            num_records += len(vals)
            num_bad += int((~is_num).sum())
            continue
        sp_records += len(vals)
        sp_bad += int((vals != vals.str.strip()).sum())
        if not _skip_for_labels(c, vals):
            lv_records += len(vals)
            b, ex = label_variants(vals)
            lv_bad += b
            lv_examples += [f"{c}: {e}" for e in ex]
    if num_records:
        add("Standard format", "Mixed types", "Numbers mixed with text in a number column",
            num_records, num_bad)
    if lv_records:
        add("Standard format", "Label variants",
            "Same label written in different ways (case, spaces, underscores)",
            lv_records, lv_bad, ("Examples: " + "; ".join(lv_examples[:3])) if lv_bad else "")
    if sp_records:
        add("Standard format", "Extra spaces", "Text values with extra spaces at the start or end",
            sp_records, sp_bad)

    for c, label, test in spec.formats:
        if c not in df.columns:
            continue
        vals = filled[c]
        if len(vals) == 0:
            continue
        bad = vals[~vals.map(lambda v: _passes(test, v))]
        add("Standard format", "Wrong format", f'"{c}" not in the expected format ({label})',
            len(vals), len(bad), f'Example: "{bad.iloc[0]}"' if len(bad) else "")

    for c, (allowed, why) in spec.allowed.items():
        if c not in df.columns:
            continue
        vals = filled[c]
        if len(vals) == 0:
            continue
        # 1.0 and 1 are the same code
        bad = vals[~(vals.isin(allowed) | vals.str.replace(r"\.0+$", "", regex=True).isin(allowed))]
        ex = ", ".join(f'"{v}"' for v in bad.value_counts().index[:3])
        add("Standard format", "Not allowed value", f'"{c}" values not in the allowed list ({why})',
            len(vals), len(bad), f"Examples: {ex}" if ex else "")

    if spec.int_cols:
        ints = [c for c in spec.int_cols if c in df.columns]
        rec = bad = style = 0
        ex = []
        for c in ints:
            vals = filled[c]
            rec += len(vals)
            dot0 = vals.str.fullmatch(r"[+-]?\d+\.0+")
            whole = vals.str.fullmatch(r"[+-]?\d+")
            wrong = ~(dot0 | whole)
            bad += int(wrong.sum())
            style += int(dot0.sum())
            if wrong.any() and len(ex) < 3:
                ex.append(f'{c}: {int(wrong.sum())} (e.g. "{vals[wrong].iloc[0]}")')
        add("Standard format", "Wrong format",
            f"Whole-number columns (per data dictionary) with values that are not whole numbers "
            f"({_n(len(ints), 'column')})", rec, bad, "; ".join(ex))
        add("Standard format", "Format style",
            f"Whole-number columns written with a trailing .0, for example 1188.0 ({_n(len(ints), 'column')})",
            rec, style, "The value is right but stored as a decimal. Software that expects an "
            "integer may reject it.")
    if spec.float_cols:
        fl = [c for c in spec.float_cols if c in df.columns]
        rec = bad = 0
        for c in fl:
            vals = filled[c]
            rec += len(vals)
            bad += int((~vals.str.fullmatch(NUMBER.pattern)).sum())
        add("Standard format", "Wrong format",
            f"Decimal columns (per data dictionary) with values that are not numbers ({_n(len(fl), 'column')})",
            rec, bad)

    for f in spec.extra:
        for ch in f(df):
            ch.details = " ".join(x for x in (note, ch.details) if x)
            checks.append(ch)

    missing_row = {"required_fields": ", ".join(spec.required),
                   "required_why": spec.required_why,
                   "required_cells": req_cells, "required_missing": req_miss,
                   "optional_cells": opt_cells, "optional_missing": opt_miss}
    return checks, columns, missing_row


def profile_matrix(path_or_lines, gene_label, gene_pattern, sep="\t", skip=0, note=""):
    """Count matrix (genes by samples). Read line by line so big files fit in memory.

    Every cell is required. Counts must be whole numbers of 0 or more.
    """
    gene_re = re.compile(gene_pattern)
    count_re = re.compile(r"\d+(\.0+)?")
    lines = iter(path_or_lines)
    for _ in range(skip):
        next(lines)
    header = next(lines).rstrip("\n").split(sep)
    first_data = 2 if header[1].lower() in ("description", "name", "gene_name") else 1
    samples = header[first_data:]
    n_genes = cells = missing = not_count = bad_gene = 0
    genes = set()
    dup_genes = 0
    for line in lines:
        parts = line.rstrip("\n").split(sep)
        n_genes += 1
        g = parts[0]
        if g in genes:
            dup_genes += 1
        genes.add(g)
        if not gene_re.fullmatch(g):
            bad_gene += 1
        vals = parts[first_data:]
        if len(vals) < len(samples):
            missing += len(samples) - len(vals)
        for v in vals:
            cells += 1
            t = v.strip()
            # a count of 99999 is a real count, so only text placeholders count here
            if t == "" or (t.lower() in HIDDEN_MISSING and not t.lstrip("-").isdigit()):
                missing += 1
            elif not count_re.fullmatch(t):
                not_count += 1
    total = n_genes * len(samples)
    checks = [
        Check("Missing values", "Missing required",
              "Missing values in the count matrix (every cell is required)", total, missing, note),
        Check("Duplicates", "Duplicate IDs", "Repeated gene IDs", n_genes, dup_genes, note),
        Check("Duplicates", "Duplicate IDs", "Repeated sample columns", len(samples),
              len(samples) - len(set(samples)), note),
        Check("Standard format", "Wrong format", "Counts that are not whole numbers of 0 or more",
              total, not_count, note),
        Check("Standard format", "Wrong format",
              f"Gene IDs not in the expected format ({gene_label})", n_genes, bad_gene, note),
    ]
    missing_row = {"required_fields": "every count cell",
                   "required_why": "A count matrix has one value per gene and sample.",
                   "required_cells": total, "required_missing": missing,
                   "optional_cells": 0, "optional_missing": 0}
    return checks, n_genes, missing_row

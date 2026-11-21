"""Command line.

  python -m qualitycheck list
  python -m qualitycheck run gtex hmp        (one or more repositories)
  python -m qualitycheck run all
  python -m qualitycheck report              (workbook from results/*.json)
  python -m qualitycheck file my_table.csv --required id,sex --ids id
"""

import argparse
import json
import sys
from pathlib import Path

from . import run as R


def cmd_list(_):
    for key in R.REPOS:
        mod = __import__(f"qualitycheck.repos.{key}", fromlist=["NAME"])
        print(f"{key:16} {mod.NAME}")


def cmd_run(args):
    keys = R.REPOS if args.repos == ["all"] else args.repos
    bad = [k for k in keys if k not in R.REPOS]
    if bad:
        sys.exit(f"unknown repository: {', '.join(bad)} (see: python -m qualitycheck list)")
    failed = []
    for key in keys:
        print(f"{key}")
        try:
            res = R.run_repo(key)
        except Exception as err:  # keep going, one site being down should not stop the rest
            print(f"  could not finish {key}: {err}")
            failed.append(key)
            continue
        print(f"  saved {R.save(res)}")
    if failed:
        print("not finished: " + ", ".join(failed))
        sys.exit(1)


def cmd_report(args):
    from .report import build
    out = build(Path(args.results), Path(args.out))
    print(f"wrote {out}")


def cmd_file(args):
    import pandas as pd

    from .checks import TableSpec, _n, profile
    from .fetch import read_text_table
    from .limits import load_limits, missing_score
    for path in (args.path, args.limits):
        if path and not Path(path).is_file():
            sys.exit(f"not found: {path}")
    sep = args.sep or ("\t" if args.path.endswith((".tsv", ".txt", ".tab")) else ",")
    try:
        df = read_text_table(args.path, sep=sep)
    except pd.errors.EmptyDataError:
        sys.exit(f"{args.path} is empty")
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()] if s else []
    spec = TableSpec(required=split(args.required), ids=split(args.ids),
                     keys=[split(args.key)] if args.key else [],
                     required_why=args.why or "")
    limits = load_limits(args.limits)
    checks, cols, miss = profile(df, spec, args.path)
    rows = [c.as_dict(limits) for c in checks]
    score = missing_score(miss["required_cells"], miss["required_missing"],
                          miss["optional_cells"], miss["optional_missing"], limits)
    print(f"{args.path}: {_n(len(df), 'row')}, {_n(df.shape[1], 'column')}")
    if df.shape[1] == 1 and "," in str(df.columns[0]):
        print("  note: only one column found, try --sep ,")
    for c in spec.required + spec.ids + [k for key in spec.keys for k in key]:
        if c not in df.columns:
            print(f"  note: column '{c}' is not in the file")
    for r in rows:
        print(f"  {r['result']:10} {r['area']:16} {r['problems']:>9,} / {r['records']:<11,} {r['check']}")
    if score is not None:
        print(f"  missing values score: {score:.1f}")
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"checks": rows, "columns": cols,
                                   "missing": miss, "score": score}, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m qualitycheck",
                                description="CFDE Data Quality Assessment: missing values, duplicates and standard format checks.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="show the repositories").set_defaults(f=cmd_list)
    r = sub.add_parser("run", help="download and check one or more repositories")
    r.add_argument("repos", nargs="+")
    r.set_defaults(f=cmd_run)
    w = sub.add_parser("report", help="build the Excel workbook from results/")
    w.add_argument("--results", default="results")
    w.add_argument("--out", default="CFDE-Data-Quality-Assessment.xlsx")
    w.set_defaults(f=cmd_report)
    f = sub.add_parser("file", help="check your own CSV or TSV file")
    f.add_argument("path")
    f.add_argument("--required", help="required columns, comma separated")
    f.add_argument("--ids", help="columns that must be unique, comma separated")
    f.add_argument("--key", help="columns that together must be unique, comma separated")
    f.add_argument("--why", help="where the required list comes from")
    f.add_argument("--sep", help="column separator (default: from the file name)")
    f.add_argument("--limits", help="your own limits.json")
    f.add_argument("--json", help="also save the results to this file")
    f.set_defaults(f=cmd_file)
    args = p.parse_args(argv)
    args.f(args)


if __name__ == "__main__":
    main()

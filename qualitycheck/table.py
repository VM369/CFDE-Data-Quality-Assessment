from dataclasses import dataclass, field


@dataclass
class Table:
    """One table to check.

    Give either df + spec (a normal table) or matrix (a dict of arguments for
    checks.profile_matrix, for genes by samples count files).
    """
    label: str
    source: str
    df: object = None
    spec: object = None
    matrix: dict = field(default=None)

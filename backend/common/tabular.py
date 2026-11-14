"""Helpers for the heterogeneous PSI experimental-table CSVs.

Each investigation publishes its own test matrix with its own column names, units and
notation ("0.17; 0.21;0.25; 0.3", "~ 21.5", "21.5 - 21.7", "30 cm/s", "RAMPED", ...).
These helpers turn that into clean rows and numbers.
"""

from __future__ import annotations

import csv
import io
import re

_NUM_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def parse_csv(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse CSV text into (header, rows); trims BOMs, blank rows and blank trailing columns."""
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    raw = [[c.replace("﻿", "").strip() for c in row] for row in reader]
    raw = [r for r in raw if any(c for c in r)]
    if not raw:
        return [], []
    header = raw[0]
    width = max(len(r) for r in raw)
    header += [""] * (width - len(header))
    rows = [r + [""] * (width - len(r)) for r in raw[1:]]
    # drop columns that are empty everywhere (header and data)
    keep = [i for i in range(width) if header[i] or any(r[i] for r in rows)]
    header = [re.sub(r"\s+", " ", header[i]).strip() or f"Column {i + 1}" for i in keep]
    rows = [[r[i] for i in keep] for r in rows]
    # make header names unique
    seen: dict[str, int] = {}
    for i, h in enumerate(header):
        if h in seen:
            seen[h] += 1
            header[i] = f"{h} ({seen[h]})"
        else:
            seen[h] = 1
    return header, rows


def numbers_in(value: str) -> list[float]:
    """All numbers in a cell. '0.17; 0.21;0.25; 0.3' -> [0.17, 0.21, 0.25, 0.3]."""
    if not value:
        return []
    # drop chemical formulas / identifiers ("LOW O2", "C2H4", "S1C2") so subscripts aren't read as values
    cleaned = re.sub(r"\b[A-Za-z]+\d[\w]*", " ", str(value))
    # treat "1.5 - 5" as a range rather than a negative number
    cleaned = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " ", cleaned)
    out = []
    for m in _NUM_RE.findall(cleaned):
        try:
            out.append(float(m))
        except ValueError:
            pass
    return out


def parse_number(value: str) -> float | None:
    """Single representative number for a cell (mean of a range), else None."""
    if value is None:
        return None
    v = str(value).strip()
    if not v or v.lower() in {"n/a", "na", "none", "-", "?", "ramped", "insignificant"}:
        return None
    # dates / times / ids are not measurements
    if re.search(r"\d{1,2}[:/]\d{1,2}[:/]\d{2,4}", v) or re.match(r"^\d{1,2}:\d{2}", v):
        return None
    if re.search(r"[a-df-zA-DF-Z]{3,}\d", v):  # e.g. 'f068a03'
        return None
    nums = numbers_in(v)
    if not nums:
        return None
    if len(nums) == 2 and re.search(r"\d\s*-\s*\d", v):
        return (nums[0] + nums[1]) / 2
    if len(nums) == 1:
        return nums[0]
    return None


def column_profile(header: list[str], rows: list[list[str]]) -> list[dict]:
    """Describe each column: numeric?, distinct values, varied-or-constant."""
    cols = []
    for i, name in enumerate(header):
        values = [r[i] for r in rows if i < len(r) and r[i] != ""]
        nums = [parse_number(v) for v in values]
        numeric_vals = [n for n in nums if n is not None]
        numeric = bool(values) and len(numeric_vals) / len(values) >= 0.6 and len(numeric_vals) >= 2
        distinct = sorted(set(values))
        col = {
            "name": name,
            "numeric": numeric,
            "filled": len(values),
            "distinct": len(distinct),
            "varied": len(distinct) > 1,
            "examples": distinct[:6],
        }
        if numeric:
            col["min"] = min(numeric_vals)
            col["max"] = max(numeric_vals)
        cols.append(col)
    return cols

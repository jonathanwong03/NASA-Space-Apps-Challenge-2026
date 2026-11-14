"""Turns a PSI investigation + its test tables into a structured fire-safety profile.

The profile is what makes cross-investigation comparison and ranking possible:
O2 / pressure / flow envelopes, fuels, what varied vs. what was held constant, the
sensors used, and which fire-safety pillar it informs.
"""

from __future__ import annotations

import math
import re

from common.tabular import numbers_in, parse_number

from .curated import FUEL_ALIASES, INVESTIGATION_TAGS, MEASUREMENT_TERMS

PSI_TO_ATM = 1 / 14.696

# ---------------------------------------------------------------- column classification


def _is_o2_col(name: str) -> bool:
    n = name.lower()
    if any(x in n for x in ("mg", "rate", "mo2", "final", "after", "flow")):
        return False
    return bool(
        re.search(r"\bx\s*o2\b|\bxo2\b|percent o2|oxygen|\bo2\b|^o initial", n)
    )


def _is_pressure_col(name: str) -> bool:
    n = name.lower()
    if any(x in n for x in ("final", "pfinal", "transducer")):
        return False
    return bool(re.search(r"pressure|\bp\s*\(|\bpinit\b|\bpmean\b|approx p", n))


def _is_flow_col(name: str) -> bool:
    n = name.lower()
    if any(x in n for x in ("restrictor", "display", "mfc", "sccm", "mg/s", "direction")):
        return False
    return ("flow" in n or "velocity" in n or "air rate" in n) and (
        "cm/s" in n or "velocity" in n or "air flow" in n
    )


def _is_fuel_col(name: str) -> bool:
    n = name.lower()
    if any(x in n for x in ("rate", "mfc", "conc", "camera", "number", "#", "thickness",
                            "length", "width", "xfuel", "xf ", "mfuel", "mg")):
        return False
    return any(x in n for x in ("fuel", "material", "sample type", "sample (fuel"))


_BOOKKEEPING = re.compile(
    r"(\bdate\b|\bgmt\b|identifier|\bid\b|#|\bnumber\b|camera|\bnotes?\b|\bcomments?\b|\byear\b|\bmonth\b|"
    r"\bday\b|session|local time|\bcir\b|^pi$|frames|radiometer gain|^test$|^flex number$)", re.I)


def _is_bookkeeping_col(name: str) -> bool:
    """Run IDs, dates, clock times, camera files... - not experimental variables."""
    return bool(_BOOKKEEPING.search(name.strip()))


def _is_atmosphere_col(name: str) -> bool:
    return "atmosphere" in name.lower() or "ambient gas" in name.lower()


# ---------------------------------------------------------------- value conversion


def _o2_values(cell: str) -> list[float]:
    vals = []
    for v in numbers_in(cell):
        if v <= 1.0:
            v *= 100.0  # mole fraction -> %
        if 0 < v <= 100:
            vals.append(round(v, 2))
    return vals


def _pressure_values(cell: str, header: str) -> list[float]:
    """Return pressures in atm."""
    h = header.lower()
    c = cell.lower()
    out = []
    for v in numbers_in(cell):
        if v <= 0:
            continue
        if "mmhg" in h or "mmhg" in c or "torr" in h:
            atm = v / 760.0
        elif "bar" in h or "bar" in c:
            atm = v * 0.986923
        elif "psi" in h or "psi" in c:
            atm = v * PSI_TO_ATM
        elif "kpa" in h or "kpa" in c:
            atm = v / 101.325
        elif v > 200:
            atm = v / 760.0
        else:
            atm = v
        if 0.01 < atm < 10:
            out.append(round(atm, 4))
    return out


def _flow_values(cell: str) -> list[float]:
    return [v for v in numbers_in(cell) if 0 <= v < 500]


def _normalize_fuel(value: str) -> str | None:
    v = re.sub(r"\s+", " ", value.split(":")[0]).strip().strip(",")
    low = v.lower()
    if not v or "pre-test" in low or "data for" in low or low in {"ramp", "ramped", "-", "n/a"} \
            or parse_number(v) is not None:
        return None
    if len(v) > 60:
        v = v[:57].rsplit(" ", 1)[0] + "..."
    for k, alias in FUEL_ALIASES.items():
        if re.search(rf"\b{k}\b", low):
            if "%" in v:
                return f"{alias} ({v})"
            return alias
    return v[:80]


# ---------------------------------------------------------------- main entry


def _range(vals: list[float]) -> dict | None:
    if not vals:
        return None
    return {"min": round(min(vals), 3), "max": round(max(vals), 3)}


def build_profile(inv: dict, tables: list[dict]) -> dict:
    """inv: normalized investigation dict; tables: [{name, header, rows}]."""
    acc = inv["accession"]
    tags = INVESTIGATION_TAGS.get(acc, {})

    o2_all: list[float] = []
    p_all: list[float] = []
    flow_all: list[float] = []
    fuels: dict[str, int] = {}
    variables: dict[str, list] = {}
    constants: dict[str, str] = {}
    points: list[dict] = []
    test_count = 0

    for t in tables:
        header, rows = t["header"], t["rows"]
        test_count += len(rows)
        o2_idx = [i for i, h in enumerate(header) if _is_o2_col(h)]
        p_idx = [i for i, h in enumerate(header) if _is_pressure_col(h)]
        f_idx = [i for i, h in enumerate(header) if _is_flow_col(h)]
        fuel_idx = [i for i, h in enumerate(header) if _is_fuel_col(h)]
        atm_idx = [i for i, h in enumerate(header) if _is_atmosphere_col(h)]

        for i, h in enumerate(header):
            vals = [r[i] for r in rows if i < len(r) and r[i]]
            distinct = sorted(set(vals))
            if not distinct or len(h) > 60 or _is_bookkeeping_col(h):
                continue
            if len(distinct) == 1 and len(vals) > 1:
                constants[h] = distinct[0][:80]
            elif len(distinct) > 1:
                nums = [parse_number(v) for v in vals]
                nums = [n for n in nums if n is not None]
                if len(nums) >= 0.6 * len(vals) and len(nums) >= 2:
                    variables[h] = [round(min(nums), 4), round(max(nums), 4)]
                else:
                    variables[h] = distinct[:5]

        for r in rows:
            row_o2: list[float] = []
            row_p: list[float] = []
            for i in o2_idx:
                row_o2 += _o2_values(r[i]) if i < len(r) else []
            for i in atm_idx:
                if i < len(r):
                    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*o2", r[i].lower())
                    if m:
                        row_o2.append(float(m.group(1)))
            for i in p_idx:
                row_p += _pressure_values(r[i], header[i]) if i < len(r) else []
            for i in f_idx:
                flow_all += _flow_values(r[i]) if i < len(r) else []
            for i in fuel_idx:
                if i < len(r) and r[i] and len(r[i]) < 120:
                    name = _normalize_fuel(r[i])
                    if name:
                        fuels[name] = fuels.get(name, 0) + 1
            o2_all += row_o2
            p_all += row_p
            for o in row_o2[:4]:
                points.append({"o2": o, "p_atm": row_p[0] if row_p else None})

    # Fallbacks: tests run in ISS cabin air when the table does not list O2 / pressure.
    phase = tags.get("phase", "unknown")
    assumed = []
    flight = "international space station" in (inv.get("flight_platform") or "").lower() or \
        "cygnus" in (inv.get("flight_platform") or "").lower()
    if not o2_all and flight:
        o2_all = [21.0]
        assumed.append("O2 assumed ~21% (ISS cabin air) - not listed in test table")
    if not p_all and (flight or o2_all):
        p_all = [1.0]
        assumed.append("Pressure assumed ~1 atm (ISS cabin) - not listed in test table")
    for pt in points:
        if pt["p_atm"] is None:
            pt["p_atm"] = p_all[0] if p_all else 1.0
    if not points and o2_all and p_all:
        points = [{"o2": o2_all[0], "p_atm": p_all[0]}]

    # de-duplicate condition points
    seen = set()
    uniq = []
    for pt in points:
        key = (round(pt["o2"] * 2) / 2, round(pt["p_atm"], 2))
        if key not in seen:
            seen.add(key)
            uniq.append({"o2": key[0], "p_atm": key[1]})
    points = uniq[:200]

    text = " ".join(
        (inv.get(k) or "") for k in ("objective", "hypothesis", "approach", "keywords", "title")
    ).lower()
    measurements = [label for label, terms in MEASUREMENT_TERMS.items() if any(t in text for t in terms)]

    pillars = tags.get("pillars") or _keyword_pillars(text)
    primary = max(pillars, key=pillars.get) if pillars else "prevention"

    o2r = _range(o2_all)
    pr = _range(p_all)
    if pr:
        pr["min_psi"] = round(pr["min"] * 14.696, 2)
        pr["max_psi"] = round(pr["max"] * 14.696, 2)

    top_fuels = sorted(fuels.items(), key=lambda kv: -kv[1])
    return {
        "fuel_phase": phase,
        "fuels": [f for f, _ in top_fuels[:12]],
        "geometry": tags.get("geometry", ""),
        "hardware_family": tags.get("hardware", "Other / not specified"),
        "tier": tags.get("tier", "supporting"),
        "summary": tags.get("summary", ""),
        "partial_gravity_proxy": bool(tags.get("partial_gravity")),
        "pillars": pillars,
        "primary_pillar": primary,
        "o2": o2r,
        "pressure_atm": pr,
        "flow_cm_s": _range(flow_all),
        "points": points,
        "test_count": test_count,
        "table_count": len(tables),
        "variables": dict(list(variables.items())[:25]),
        "constants": dict(list(constants.items())[:25]),
        "measurements": measurements,
        "assumptions": assumed,
        "data_richness": round(min(1.0, math.log10(1 + test_count) / 2.5 * 0.7
                                   + min(len(inv.get("publications") or []), 40) / 40 * 0.3), 3),
    }


def _keyword_pillars(text: str) -> dict:
    def score(words):
        return min(1.0, sum(text.count(w) for w in words) / 6)

    return {
        "prevention": score(["flammab", "ignition", "flame spread", "material", "oxygen concentration"]),
        "detection": score(["smoke", "detect", "aerosol", "soot", "particle"]),
        "suppression": score(["extinguish", "suppress", "extinction", "diluent", "quench"]),
    }

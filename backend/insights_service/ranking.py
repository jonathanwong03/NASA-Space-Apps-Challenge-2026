"""Explainable relevance ranking of investigations for a crewed-habitat scenario.

Every score is a weighted sum of transparent components so researchers can see *why*
an investigation ranks where it does - and disagree with the weights if they like.
"""

from __future__ import annotations

import math

ATM_TO_PSI = 14.696
NEAR_TOL = 0.05  # "near the envelope": within 5% of the habitat's O2 / pressure bounds

WEIGHTS = {
    "pillar": 0.25,      # does it inform prevention / detection / suppression?
    "directness": 0.10,  # explicitly a spacecraft fire-safety investigation?
    "oxygen": 0.20,      # tested O2 vs. habitat O2
    "pressure": 0.10,    # tested pressure vs. habitat pressure
    "flow": 0.05,        # tested ventilation flow vs. habitat
    "fuel": 0.15,        # how representative is the fuel of what burns in a habitat
    "gravity": 0.05,     # gravity-level relevance
    "data": 0.10,        # amount of extractable test data + publications
}

FUEL_RELEVANCE = {"solid": 1.0, "aerosol": 0.85, "liquid": 0.6, "gas": 0.5}
SOLID_EMULATORS = {"PSI-20"}  # ACME BRE: gaseous fuel that emulates burning solids
PHASE_WORDS = {
    "solid": "Solid materials (fabrics, plastics): directly representative of cabin fire loads",
    "aerosol": "Smoke/dust aerosols: drives detector design and false-alarm rejection",
    "liquid": "Liquid-fuel droplets: physics of extinction and cool flames",
    "gas": "Gaseous flames: fundamental flame physics, soot and extinction limits",
}


def _band_score(lo, hi, band_lo, band_hi, scale) -> tuple[float, float]:
    """1.0 if tested range overlaps the band, else decays with distance. Returns (score, gap)."""
    if hi >= band_lo and lo <= band_hi:
        return 1.0, 0.0
    gap = band_lo - hi if hi < band_lo else lo - band_hi
    return math.exp(-gap / scale), gap


def score(inv: dict, hab: dict, focus: str = "all") -> dict:
    p = inv["profile"]
    pillars = p.get("pillars") or {}
    comps, reasons = {}, []

    # pillar
    if focus in ("prevention", "detection", "suppression"):
        comps["pillar"] = pillars.get(focus, 0.0)
    else:
        vals = list(pillars.values()) or [0]
        comps["pillar"] = 0.6 * max(vals) + 0.4 * (sum(vals) / len(vals))
    top = p.get("primary_pillar")
    if top:
        reasons.append(f"Informs fire {top} (pillar weight {pillars.get(top, 0):.1f})")

    # directness
    comps["directness"] = 1.0 if p.get("tier") == "direct" else 0.55
    if p.get("tier") == "direct":
        reasons.append("Named spacecraft fire-safety investigation")

    # oxygen
    o2 = p.get("o2")
    if o2:
        s, gap = _band_score(o2["min"], o2["max"], hab["o2_min"], hab["o2_max"], 8.0)
        comps["oxygen"] = s
        if gap == 0:
            reasons.append(f"Tested O2 {o2['min']:g}-{o2['max']:g}% covers the {hab['short']} band "
                           f"({hab['o2_min']:g}-{hab['o2_max']:g}%)")
        else:
            reasons.append(f"Tested O2 {o2['min']:g}-{o2['max']:g}%, {gap:.0f} points outside the "
                           f"{hab['short']} band. Extrapolation needed")
    else:
        comps["oxygen"] = 0.3
        reasons.append("No O2 conditions in published test table (analysis/modeling study)")

    # pressure
    pr = p.get("pressure_atm")
    if pr:
        lo, hi = pr["min"] * ATM_TO_PSI, pr["max"] * ATM_TO_PSI
        s, gap = _band_score(lo, hi, hab["p_min_psi"], hab["p_max_psi"], 3.0)
        comps["pressure"] = s
        if gap == 0:
            reasons.append(f"Pressure range {lo:.1f}-{hi:.1f} psi overlaps the habitat's "
                           f"{hab['p_min_psi']:g}-{hab['p_max_psi']:g} psi")
        elif hab["p_max_psi"] < lo:
            reasons.append(f"Tested at >= {lo:.1f} psi only; habitat runs at "
                           f"{hab['p_min_psi']:g}-{hab['p_max_psi']:g} psi")
    else:
        comps["pressure"] = 0.3

    # flow
    fl = p.get("flow_cm_s")
    if fl:
        s, _ = _band_score(fl["min"], fl["max"], hab["flow_min"], hab["flow_max"], 10.0)
        comps["flow"] = s
        reasons.append(f"Imposed flow {fl['min']:g}-{fl['max']:g} cm/s "
                       f"(habitat ventilation ~{hab['flow_min']:g}-{hab['flow_max']:g} cm/s)")
    else:
        comps["flow"] = 0.5

    # fuel
    phase = p.get("fuel_phase", "gas")
    comps["fuel"] = 0.85 if inv["accession"] in SOLID_EMULATORS else FUEL_RELEVANCE.get(phase, 0.4)
    if inv["accession"] in SOLID_EMULATORS:
        reasons.append("Gaseous burner emulates burning solid materials (BRE)")
    elif phase in PHASE_WORDS:
        reasons.append(PHASE_WORDS[phase])

    # gravity
    flight = "ground" not in (inv.get("project_type") or "").lower()
    g = hab["gravity_g"]
    if g == 0:
        comps["gravity"] = 1.0 if flight else 0.7
    elif g >= 1:
        comps["gravity"] = 0.6
        reasons.append("Microgravity removes buoyancy, which isolates the physics behind terrestrial detection and suppression")
    else:
        comps["gravity"] = 1.0 if p.get("partial_gravity_proxy") else 0.55
        if p.get("partial_gravity_proxy"):
            reasons.append("Electric field mimics buoyancy, the only partial-gravity proxy in PSI")
        else:
            reasons.append(f"Microgravity result. Bounds {g:g} g behavior together with 1 g data")

    comps["data"] = p.get("data_richness", 0.0)
    if p.get("test_count"):
        reasons.append(f"{p['test_count']} test records across {p.get('table_count', 0)} table(s), "
                       f"{len(inv.get('publications') or [])} publications")

    total = sum(WEIGHTS[k] * comps[k] for k in WEIGHTS)
    return {
        "accession": inv["accession"], "label": inv["label"], "title": inv["title"],
        "score": round(total * 100, 1),
        "components": {k: round(v, 3) for k, v in comps.items()},
        "weighted": {k: round(WEIGHTS[k] * comps[k] * 100, 1) for k in WEIGHTS},
        "reasons": reasons,
        "fuel_phase": phase, "tier": p.get("tier"), "primary_pillar": top,
        "o2": o2, "pressure_atm": pr, "summary": p.get("summary", ""),
    }


def rank(investigations: list[dict], hab: dict, focus: str = "all", limit: int | None = None) -> list[dict]:
    ranked = sorted((score(i, hab, focus) for i in investigations), key=lambda r: -r["score"])
    for n, r in enumerate(ranked, 1):
        r["rank"] = n
    return ranked[:limit] if limit else ranked


# ------------------------------------------------------------------------- gap analysis


def _in_box(pt, hab, tol: float = 0.0):
    """Inside the habitat's O2 x pressure box, optionally widened by a relative tolerance."""
    psi = pt["p_atm"] * ATM_TO_PSI
    return (hab["o2_min"] * (1 - tol) <= pt["o2"] <= hab["o2_max"] * (1 + tol)
            and hab["p_min_psi"] * (1 - tol) <= psi <= hab["p_max_psi"] * (1 + tol))


def gaps(investigations: list[dict], habitats: dict) -> dict:
    per_scenario = []
    for hab in habitats.values():
        o2_cov, full_cov, near_cov, points_in, points_near = [], [], [], 0, 0
        total_points = 0
        for inv in investigations:
            p = inv["profile"]
            pts = p.get("points") or []
            total_points += len(pts)
            inside = [pt for pt in pts if _in_box(pt, hab)]
            near = [pt for pt in pts if _in_box(pt, hab, NEAR_TOL) and not _in_box(pt, hab)]
            points_in += len(inside)
            points_near += len(near)
            if near and not inside:
                near_cov.append(inv["label"])
            o2 = p.get("o2")
            if o2 and o2["max"] >= hab["o2_min"] and o2["min"] <= hab["o2_max"]:
                o2_cov.append(inv["label"])
            if inside:
                full_cov.append(inv["label"])
        solid_cov = [i["label"] for i in investigations
                     if i["profile"].get("fuel_phase") == "solid"
                     and (i["profile"].get("o2") or {}).get("max", 0) >= hab["o2_min"]]
        per_scenario.append({
            "slug": hab["slug"], "name": hab["name"], "short": hab["short"],
            "o2_band": [hab["o2_min"], hab["o2_max"]], "p_band_psi": [hab["p_min_psi"], hab["p_max_psi"]],
            "investigations_o2_overlap": o2_cov,
            "investigations_in_envelope": full_cov,
            "investigations_near_envelope": near_cov,
            "solid_material_coverage": solid_cov,
            "points_in_envelope": points_in, "points_near_envelope": points_near,
            "near_tolerance": NEAR_TOL, "total_points": total_points,
            "coverage": "good" if len(full_cov) >= 3 and solid_cov else
                        "partial" if o2_cov else "none",
        })

    findings = []
    profiles = [(i, i["profile"]) for i in investigations]
    solids = [(i, p) for i, p in profiles if p.get("fuel_phase") == "solid"]
    solid_max = max([(p.get("o2") or {}).get("max", 0) for _, p in solids] or [0])
    moon = habitats.get("lunar_base")
    if moon:
        high_o2 = [i["label"] for i, p in profiles if (p.get("o2") or {}).get("max", 0) >= moon["o2_min"]]
        findings.append({
            "severity": "critical",
            "title": f"No solid-material flammability data above ~{solid_max:.0f}% O2",
            "detail": f"Every BASS, BASS-II and Saffire test on fabrics and plastics ran in near-Earth air "
                      f"(max {solid_max:.1f}% O2, ~1 atm). The Moon Base and rovers are expected at >= "
                      f"{moon['o2_min']:.0f}% O2 and <= {moon['p_max_psi']:.1f} psi, where materials are much "
                      f"more flammable. Material-selection data for those atmospheres must still come from 1 g "
                      f"tests (NASA-STD-6001) or from extrapolation.",
            "investigations": [i["label"] for i, _ in solids],
        })
        findings.append({
            "severity": "warning",
            "title": f"Only {len(high_o2)} investigations reach Moon Base O2 levels",
            "detail": "These gas- and droplet-flame studies give the only microgravity evidence at >= 30% O2, "
                      "including CFI-G oxidizer streams up to ~85% O2. They are the anchor points for models "
                      "that extrapolate solid-material behavior.",
            "investigations": high_o2,
        })
    pg = [i["label"] for i, p in profiles if p.get("partial_gravity_proxy")]
    findings.append({
        "severity": "serious",
        "title": "No partial-gravity (Moon 0.17 g / Mars 0.38 g) combustion data in PSI",
        "detail": "Microgravity and 1 g results have to bracket partial-gravity behavior until LUCI and FM2 data "
                  "arrive. "
                  + (f"{', '.join(pg)} uses electric fields to mimic buoyancy as a proxy." if pg else ""),
        "investigations": pg,
    })
    det = [(i, p) for i, p in profiles if p.get("primary_pillar") == "detection"]
    det_p = [(p.get("pressure_atm") or {}).get("min", 1) for _, p in det]
    if det:
        findings.append({
            "severity": "warning",
            "title": "Smoke & aerosol data collected only at cabin pressure",
            "detail": f"SAME, SAME-R and DAFT characterize smoke and dust particle sizes at ~{min(det_p):.1f} atm. "
                      "Smoke formation and transport at 8-10 psi with higher O2 has not been tested, and that "
                      "matters for detector thresholds and for nuisance-alarm rejection (Artemis II).",
            "investigations": [i["label"] for i, _ in det],
        })
    moon_cov = next((s for s in per_scenario if s["slug"] == "lunar_base"), None)
    if moon and moon_cov and not moon_cov["investigations_in_envelope"] and moon_cov["investigations_near_envelope"]:
        near_pts = [(pt, i["label"]) for i in investigations for pt in (i["profile"].get("points") or [])
                    if _in_box(pt, moon, NEAR_TOL)]
        o2s = sorted({pt["o2"] for pt, _ in near_pts})
        psis = sorted({round(pt["p_atm"] * ATM_TO_PSI, 1) for pt, _ in near_pts})
        names = {"gas": "gaseous", "liquid": "liquid-droplet", "solid": "solid", "aerosol": "aerosol"}
        near_phases = sorted({names.get(i["profile"].get("fuel_phase"), "other") for i in investigations
                              if i["label"] in moon_cov["investigations_near_envelope"]})
        solid_near = "solid" in near_phases
        findings.insert(2, {
            "severity": "warning",
            "title": f"Closest match to the Moon Base atmosphere: {', '.join(moon_cov['investigations_near_envelope'])}",
            "detail": f"No PSI test falls inside the Moon Base box ({moon['o2_min']:g}-{moon['o2_max']:g}% O2, "
                      f"{moon['p_min_psi']:g}-{moon['p_max_psi']:g} psi). The nearest are "
                      f"{' and '.join(near_phases)} flame tests at {o2s[0]:g}-{o2s[-1]:g}% O2 and "
                      f"{psis[0]:g}-{psis[-1]:g} psi, within {NEAR_TOL:.0%} of the box. They are the best microgravity "
                      f"anchor points for lunar-atmosphere fire models"
                      + ("." if solid_near else ", but none of them burned solid cabin materials."),
            "investigations": moon_cov["investigations_near_envelope"],
        })
    sup = [(i, p) for i, p in profiles if (p.get("pillars") or {}).get("suppression", 0) >= 0.7]
    if sup:
        o2s = [p.get("o2") for _, p in sup if p.get("o2")]
        lo = min(o["min"] for o in o2s) if o2s else 0
        hi = max(o["max"] for o in o2s) if o2s else 0
        findings.append({
            "severity": "good",
            "title": "Suppression-by-dilution data spans exploration atmospheres",
            "detail": f"FLEX/FLEX-2 measured droplet extinction with CO2 and He dilution from {lo:.0f}% to "
                      f"{hi:.0f}% O2 and sub-atmospheric pressures. That data can size inert-gas suppression "
                      f"for 30-34% O2 habitats.",
            "investigations": [i["label"] for i, _ in sup],
        })
    return {"scenarios": per_scenario, "findings": findings}

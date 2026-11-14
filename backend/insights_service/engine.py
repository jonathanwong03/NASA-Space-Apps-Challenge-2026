"""Deterministic SI engine: retrieval + rules. Used when no Claude API key is configured,
so the dashboard works fully offline and its answers are reproducible."""

from __future__ import annotations

from .ranking import gaps
from .search import Index

FOOTER = ("\n\n---\n_Offline SI engine (BM25 retrieval + explainable ranking rules). "
          "Set `ANTHROPIC_API_KEY` to enable Claude-generated answers._")


def _fmt(r, unit, scale=1.0):
    if not r:
        return "n/r"
    lo, hi = r["min"] * scale, r["max"] * scale
    return f"{lo:.3g}{unit}" if abs(hi - lo) < 1e-9 else f"{lo:.3g}-{hi:.3g}{unit}"


def extractive_answer(question: str, data: dict, scenario: dict | None, ranked: list[dict], index: Index) -> str:
    q = question.lower()
    hits = index.search(question, k=8)
    by_acc = {i["accession"]: i for i in data["investigations"]}
    rank_score = {r["accession"]: r["score"] / 100 for r in ranked}
    blended = sorted(hits, key=lambda h: -(0.65 * h["score"] + 0.35 * rank_score.get(h["accession"], 0.5)))
    if not blended and ranked:
        blended = [{"accession": r["accession"], "snippet": ""} for r in ranked[:4]]

    out = []
    if scenario:
        out.append(f"**Scenario:** {scenario['name']}: {scenario['o2_min']:g}-{scenario['o2_max']:g}% O2, "
                   f"{scenario['p_min_psi']:g}-{scenario['p_max_psi']:g} psi, {scenario['gravity_g']:g} g.\n")
    out.append("#### Most relevant evidence in PSI")
    for h in blended[:5]:
        inv = by_acc[h["accession"]]
        p = inv["profile"]
        out.append(
            f"- **[{inv['accession']} {inv['label']}]** {p.get('summary') or inv['title']}  \n"
            f"  Tested O2 {_fmt(p.get('o2'), '%')}, pressure {_fmt(p.get('pressure_atm'), ' psi', 14.696)}, "
            f"flow {_fmt(p.get('flow_cm_s'), ' cm/s')}; {p.get('test_count', 0)} test records."
            + (f"  \n  > {h['snippet']}" if h.get("snippet") else "")
        )

    g = gaps(data["investigations"], data["habitats"])
    keys = {
        "critical": ["moon", "lunar", "mars", "rover", "oxygen", "o2", "habitat", "base", "flammab", "material"],
        "serious": ["gravity", "partial", "moon", "mars", "lunar"],
        "warning": ["smoke", "detect", "alarm", "aerosol", "pressure"],
        "good": ["suppress", "extinguish", "co2", "helium", "dilution", "inert"],
    }
    relevant = [f for f in g["findings"] if any(k in q for k in keys.get(f["severity"], []))]
    if scenario and scenario["slug"] in ("lunar_base", "rover", "mars", "spacesuit") and not relevant:
        relevant = [f for f in g["findings"] if f["severity"] in ("critical", "serious")]
    if relevant:
        out.append("\n#### What the data does and does not cover")
        for f in relevant[:3]:
            out.append(f"- **{f['title']}.** {f['detail']}")

    if ranked:
        out.append(f"\n#### Highest-ranked for {scenario['short'] if scenario else 'this scenario'}")
        for r in ranked[:3]:
            out.append(f"- **{r['label']}** (score {r['score']:.0f}): " + "; ".join(r["reasons"][:3]))
    return "\n".join(out) + FOOTER


def _clip(text: str | None, n: int) -> str:
    """Trim to n chars at a sentence (or word) boundary."""
    t = " ".join((text or "").split())
    if len(t) <= n:
        return t
    cut = t[:n]
    end = cut.rfind(". ")
    return cut[: end + 1] if end > n * 0.5 else cut.rsplit(" ", 1)[0] + "..."


def _val(v) -> str:
    if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
        return f"{v[0]:g} to {v[1]:g}"
    return ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)


def template_brief(inv: dict) -> str:
    p = inv["profile"]
    var = "\n".join(f"  - {k}: {_val(v)}" for k, v in list((p.get("variables") or {}).items())[:10]) or "  - n/a"
    const = "\n".join(f"  - {k}: {v}" for k, v in list((p.get("constants") or {}).items())[:8]) or "  - n/a"
    tables = "\n".join(f"- *{t['name']}* ({t['rows']} rows): {', '.join(t['columns'][:10])}"
                       for t in inv["tables"]) or "- No test table published."
    pill = p.get("pillars") or {}
    return f"""### What it studied
{p.get('summary') or ''} {_clip(inv.get('objective'), 600)}

### Test matrix at a glance
- **Fuel phase / samples:** {p.get('fuel_phase')}, {', '.join(p.get('fuels', [])[:8]) or 'n/a'} ({p.get('geometry') or 'geometry n/a'})
- **O2:** {_fmt(p.get('o2'), '%')} | **Pressure:** {_fmt(p.get('pressure_atm'), ' atm')} | **Flow:** {_fmt(p.get('flow_cm_s'), ' cm/s')}
- **Hardware:** {p.get('hardware_family')}
- **Varied between tests:**
{var}
- **Held constant:**
{const}
- **Measurements:** {', '.join(p.get('measurements', [])) or 'n/a'}

### Key fire-safety relevance
Pillar weights: prevention {pill.get('prevention', 0):.1f}, detection {pill.get('detection', 0):.1f}, suppression {pill.get('suppression', 0):.1f} ({p.get('tier')} relevance).
{_clip(inv.get('hypothesis'), 500)}

### Data you can use for predictive modeling
{tables}

### Earth applications
{_clip(inv.get('research_impacts'), 700) or 'Not stated in the PSI record.'}
""" + FOOTER

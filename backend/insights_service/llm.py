"""Claude-powered interpretation layer (optional - enabled when ANTHROPIC_API_KEY is set).

The whole PSI combustion corpus (~24 investigations) fits comfortably in context, so
instead of a vector store we put a deterministic, compact rendering of every record in
the system prompt and mark it for prompt caching. Every question then reuses the cached
corpus, and answers can cite any investigation.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import anthropic

from common.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger("insights.llm")

FALLBACK_BETA = "server-side-fallback-2026-07-01"
client: anthropic.AsyncAnthropic | None = (
    anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY, max_retries=2, timeout=120.0) if ANTHROPIC_API_KEY else None
)

SYSTEM_RULES = """You are the analysis engine of FireSafe-SI, a dashboard that helps aerospace researchers, \
engineers and students use NASA's microgravity combustion data (the Physical Sciences Informatics, PSI, \
database) for crew fire safety on spacecraft, space stations, Moon bases, pressurized rovers and Mars habitats.

You will be given the full set of PSI combustion investigation records, each with an accession ID such as \
PSI-69, plus derived test-condition profiles, habitat atmosphere scenarios and historical incidents.

How to answer:
- Ground every factual claim in the records. Cite investigations inline by accession and acronym, e.g. \
"[PSI-69 FLEX]". If the records don't contain the answer, say so plainly and name the closest available evidence.
- Separate what was measured from what you infer. Treat extrapolation (for example from 21% O2 data to \
Moon Base atmospheres of 30% or more, or from microgravity to partial gravity) as inference, and say how \
confident it is.
- Organize fire-safety implications by NASA's pillars where it helps: prevention (ignition control, \
material flammability), detection (smoke/aerosol sensing) and suppression (extinguishment).
- When conditions matter, give the numbers from the profiles: O2 %, pressure (atm/psi), flow (cm/s), fuels \
and sample geometry.
- Rocket propulsion is out of scope for this data. Say so if asked.
- Write for technically literate readers in GitHub-flavored markdown with short headings and bullet lists. \
Keep it tight: answers usually fit in 150-400 words unless the user asks for depth."""


def enabled() -> bool:
    return client is not None


def _fmt_range(r, unit, scale=1.0, digits=3):
    if not r:
        return "not reported"
    lo, hi = r["min"] * scale, r["max"] * scale
    return f"{lo:.{digits}g}{unit}" if abs(hi - lo) < 1e-9 else f"{lo:.{digits}g}-{hi:.{digits}g}{unit}"


def corpus_text(data: dict) -> str:
    """Deterministic rendering (sorted, no timestamps) so the prompt-cache prefix stays stable."""
    parts = ["# PSI combustion investigations\n"]
    for inv in sorted(data["investigations"], key=lambda i: i["accession"]):
        p = inv["profile"]
        pubs = "; ".join(x["title"] for x in inv["publications"][:6])
        variables = ", ".join(f"{k}: {v}" for k, v in list((p.get("variables") or {}).items())[:12])
        constants = ", ".join(f"{k}={v}" for k, v in list((p.get("constants") or {}).items())[:10])
        tables = "; ".join(f"{t['name']} ({t['rows']} rows; cols: {', '.join(t['columns'][:14])})"
                           for t in inv["tables"])
        parts.append(f"""## {inv['accession']} {inv['acronym'] or ''} - {inv['title']}
Type: {inv['project_type']} | Platform: {inv['flight_platform'] or 'n/a'} | Years: {inv['start_year'] or '?'}-{inv['end_year'] or '?'} | Sub-area: {inv['sub_research_area']}
Hardware: {inv['hardware'] or 'n/a'} (family: {p.get('hardware_family')})
Fire-safety tier: {p.get('tier')} | pillars: {p.get('pillars')} | fuel phase: {p.get('fuel_phase')} | geometry: {p.get('geometry')}
Tested O2: {_fmt_range(p.get('o2'), '%')} | pressure: {_fmt_range(p.get('pressure_atm'), ' atm')} | flow: {_fmt_range(p.get('flow_cm_s'), ' cm/s')}
Fuels/materials: {', '.join(p.get('fuels', [])) or 'n/a'}
Measurements: {', '.join(p.get('measurements', [])) or 'n/a'}
Varied parameters: {variables or 'n/a'}
Held constant: {constants or 'n/a'}
Assumptions: {'; '.join(p.get('assumptions', [])) or 'none'}
Test tables: {tables or 'none published'}
Related: {', '.join(inv['related']) or 'none'} | DOI: {inv['doi']}
Objective: {(inv['objective'] or '')[:1600]}
Hypothesis: {(inv['hypothesis'] or '')[:900]}
Approach: {(inv['approach'] or '')[:1600]}
Research impacts / Earth benefits: {(inv['research_impacts'] or '')[:900]}
Selected publications: {pubs or 'n/a'}
""")
    parts.append("\n# Habitat atmosphere scenarios\n")
    for h in data["habitats"].values():
        parts.append(f"- {h['slug']}: {h['name']} - O2 {h['o2_min']:g}-{h['o2_max']:g}%, "
                     f"{h['p_min_psi']:g}-{h['p_max_psi']:g} psi, gravity {h['gravity_g']:g} g. "
                     f"{h['description']} Basis: {h['basis']}\n")
    parts.append("\n# Historical incidents\n")
    for x in data["incidents"]:
        parts.append(f"- {x['name']} ({x['date']}): {x['cause']} Outcome: {x['outcome']}\n")
    return "".join(parts)


def _system(data: dict) -> list[dict]:
    return [
        {"type": "text", "text": SYSTEM_RULES},
        {"type": "text", "text": corpus_text(data), "cache_control": {"type": "ephemeral"}},
    ]


def _context_note(scenario: dict | None, ranked: list[dict]) -> str:
    if not scenario:
        return ""
    lines = [f"Selected scenario: {scenario['name']} (O2 {scenario['o2_min']:g}-{scenario['o2_max']:g}%, "
             f"{scenario['p_min_psi']:g}-{scenario['p_max_psi']:g} psi, {scenario['gravity_g']:g} g)."]
    if ranked:
        lines.append("Top investigations from the dashboard's transparent relevance model for this scenario: " +
                     ", ".join(f"{r['accession']} {r['label']} ({r['score']:.0f})" for r in ranked[:6]) + ".")
    return "\n".join(lines) + "\n\n"


async def stream_answer(question: str, data: dict, scenario: dict | None, ranked: list[dict],
                        history: list[dict]) -> AsyncIterator[str]:
    assert client is not None
    messages = [m for m in history if m.get("role") in ("user", "assistant") and m.get("content")][-10:]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": _context_note(scenario, ranked) + question})
    try:
        async with client.beta.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            output_config={"effort": "medium"},
            system=_system(data),
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
            final = await stream.get_final_message()
            if final.stop_reason == "refusal":
                yield "\n\n_The model declined to answer this request._"
            elif final.stop_reason == "max_tokens":
                yield "\n\n_(answer truncated)_"
    except anthropic.AuthenticationError:
        yield "\n\n**SI error:** the configured `ANTHROPIC_API_KEY` was rejected."
    except anthropic.RateLimitError:
        yield "\n\n**SI error:** rate limited by the Claude API. Please retry shortly."
    except anthropic.APIStatusError as e:
        log.warning("Claude API error %s: %s", e.status_code, e.message)
        yield f"\n\n**SI error:** Claude API returned {e.status_code}."
    except anthropic.APIConnectionError:
        yield "\n\n**SI error:** could not reach the Claude API (network)."


BRIEF_PROMPT = """Write a research brief for investigation {acc} for an aerospace engineer designing \
fire-safety systems for exploration habitats. Use exactly these sections:

### What it studied
### Test matrix at a glance
(fuels / samples, O2, pressure, flow, what varied vs. held constant, sensors. Use the profile numbers.)
### Key fire-safety findings
### Relevance to Moon, Mars and rovers
(be explicit about extrapolation from the tested conditions)
### Data you can use for predictive modeling
(which tables or columns, and what model inputs or validation targets they provide)
### Earth applications

Stay grounded in the records and cite related investigations by accession where useful. Aim for about 350-500 words."""


async def brief(acc: str, data: dict) -> str:
    assert client is not None
    resp = await client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": "medium"},
        system=_system(data),
        messages=[{"role": "user", "content": BRIEF_PROMPT.format(acc=acc)}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model declined")
    return "".join(b.text for b in resp.content if b.type == "text").strip()

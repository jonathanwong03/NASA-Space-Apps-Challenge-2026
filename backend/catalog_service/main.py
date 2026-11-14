"""Catalog microservice: read API over investigations, test tables and reference data."""

from __future__ import annotations

import csv
import io
import os
from collections import Counter
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from common.db import get_session, wait_for_db
from common.models import ExperimentTable, Habitat, Incident, Investigation, Spinoff
from common.tabular import parse_number

@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    yield


app = FastAPI(title="FireSafe-SI Catalog Service", version="1.0.0", lifespan=lifespan,
              root_path=os.getenv("ROOT_PATH", ""))


PILLARS = ("prevention", "detection", "suppression")


def summary(inv: Investigation) -> dict:
    p = inv.profile or {}
    return {
        "accession": inv.accession,
        "acronym": inv.acronym,
        "title": inv.title,
        "label": inv.acronym or inv.title,
        "sub_research_area": inv.sub_research_area,
        "project_type": inv.project_type,
        "flight_platform": inv.flight_platform,
        "hardware": inv.hardware,
        "start_year": inv.start_year,
        "end_year": inv.end_year,
        "doi": inv.doi,
        "thumbnail_url": inv.thumbnail_url,
        "psi_url": inv.psi_url,
        "publication_count": len(inv.publications or []),
        "fuel_phase": p.get("fuel_phase"),
        "fuels": p.get("fuels", [])[:6],
        "hardware_family": p.get("hardware_family"),
        "tier": p.get("tier"),
        "pillars": p.get("pillars", {}),
        "primary_pillar": p.get("primary_pillar"),
        "o2": p.get("o2"),
        "pressure_atm": p.get("pressure_atm"),
        "flow_cm_s": p.get("flow_cm_s"),
        "test_count": p.get("test_count", 0),
        "summary": p.get("summary") or (inv.objective or "")[:220],
        "source": inv.source,
    }


def detail(inv: Investigation) -> dict:
    d = summary(inv)
    d.update({
        "research_area": inv.research_area,
        "managing_center": inv.managing_center,
        "hardware_link": inv.hardware_link,
        "start_date": inv.start_date,
        "end_date": inv.end_date,
        "objective": inv.objective,
        "hypothesis": inv.hypothesis,
        "approach": inv.approach,
        "research_impacts": inv.research_impacts,
        "keywords": inv.keywords,
        "related": inv.related,
        "publications": inv.publications,
        "contacts": inv.contacts,
        "profile": inv.profile,
        "tables": [
            {"id": t.id, "name": t.name, "kind": t.kind, "file_name": t.file_name,
             "row_count": t.row_count, "columns": t.columns}
            for t in inv.tables
        ],
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    })
    return d


@app.get("/health")
def health():
    return {"status": "ok", "service": "catalog"}


@app.get("/investigations")
def list_investigations(
    q: str | None = None,
    pillar: str | None = Query(None, pattern="^(prevention|detection|suppression)$"),
    phase: str | None = None,
    hardware: str | None = None,
    tier: str | None = None,
    flight_only: bool = False,
    db: Session = Depends(get_session),
):
    stmt = select(Investigation).order_by(Investigation.accession)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Investigation.title.ilike(like), Investigation.acronym.ilike(like),
                              Investigation.objective.ilike(like), Investigation.keywords.ilike(like),
                              Investigation.accession.ilike(like), Investigation.approach.ilike(like)))
    items = [summary(i) for i in db.scalars(stmt).all()]
    if pillar:
        items = [i for i in items if (i["pillars"] or {}).get(pillar, 0) >= 0.5]
    if phase:
        items = [i for i in items if i["fuel_phase"] == phase]
    if hardware:
        items = [i for i in items if i["hardware_family"] == hardware]
    if tier:
        items = [i for i in items if i["tier"] == tier]
    if flight_only:
        items = [i for i in items if "investigation" in (i["project_type"] or "").lower()
                 and "ground" not in (i["project_type"] or "").lower()]
    items.sort(key=lambda i: (i["tier"] != "direct", -(i["test_count"] or 0)))
    return items


@app.get("/investigations/{accession}")
def get_investigation(accession: str, db: Session = Depends(get_session)):
    inv = db.scalar(select(Investigation).options(selectinload(Investigation.tables))
                    .where(Investigation.accession == accession.upper()))
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return detail(inv)


@app.get("/tables")
def list_tables(db: Session = Depends(get_session)):
    rows = db.execute(
        select(ExperimentTable.id, ExperimentTable.accession, ExperimentTable.name, ExperimentTable.row_count,
               ExperimentTable.columns, Investigation.acronym)
        .join(Investigation, Investigation.accession == ExperimentTable.accession)
        .order_by(ExperimentTable.accession, ExperimentTable.id)
    ).all()
    return [
        {"id": r.id, "accession": r.accession, "label": r.acronym or r.accession, "name": r.name,
         "row_count": r.row_count, "numeric_columns": [c["name"] for c in r.columns if c.get("numeric")]}
        for r in rows
    ]


@app.get("/tables/{table_id}")
def get_table(table_id: int, db: Session = Depends(get_session)):
    t = db.get(ExperimentTable, table_id)
    if not t:
        raise HTTPException(404, "Table not found")
    header = [c["name"] for c in t.columns]
    numeric = {c["name"] for c in t.columns if c.get("numeric")}
    parsed = [
        {h: (parse_number(v) if h in numeric else v) for h, v in zip(header, row)}
        for row in t.rows
    ]
    return {"id": t.id, "accession": t.accession, "name": t.name, "file_name": t.file_name,
            "columns": t.columns, "rows": t.rows, "records": parsed}


@app.get("/tables/{table_id}/csv")
def table_csv(table_id: int, db: Session = Depends(get_session)):
    t = db.get(ExperimentTable, table_id)
    if not t:
        raise HTTPException(404, "Table not found")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([c["name"] for c in t.columns])
    w.writerows(t.rows)
    name = t.file_name if t.file_name.lower().endswith(".csv") else f"{t.file_name}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/conditions")
def conditions(db: Session = Depends(get_session)):
    """Every tested O2 / pressure condition, for the flammability-envelope map."""
    out = []
    for inv in db.scalars(select(Investigation)).all():
        p = inv.profile or {}
        for pt in p.get("points", []):
            out.append({"accession": inv.accession, "label": inv.acronym or inv.accession,
                        "phase": p.get("fuel_phase"), "o2": pt["o2"], "p_atm": pt["p_atm"],
                        "p_psi": round(pt["p_atm"] * 14.696, 2),
                        "assumed": bool(p.get("assumptions"))})
    return out


@app.get("/compare")
def compare(ids: str = Query(..., description="Comma-separated accessions"), db: Session = Depends(get_session)):
    accs = [a.strip().upper() for a in ids.split(",") if a.strip()][:4]
    invs = db.scalars(select(Investigation).where(Investigation.accession.in_(accs))).all()
    invs.sort(key=lambda i: accs.index(i.accession))
    if len(invs) < 2:
        raise HTTPException(400, "Pick at least two investigations")
    items = [detail_light(i) for i in invs]

    def shared(key):
        sets = [set(x) for x in (i[key] for i in items)]
        return sorted(set.intersection(*sets)) if sets else []

    similarities, differences = [], []
    for field, label in (("hardware_family", "Hardware"), ("fuel_phase", "Fuel phase"),
                         ("flight_platform", "Platform"), ("primary_pillar", "Primary fire-safety pillar")):
        vals = {i[field] for i in items}
        (similarities if len(vals) == 1 else differences).append(
            {"attribute": label, "values": {i["accession"]: i[field] for i in items}})
    for key, label in (("measurements", "Shared measurement types"), ("fuels", "Shared fuels"),
                       ("variable_names", "Parameters varied in both")):
        s = shared(key)
        if s:
            similarities.append({"attribute": label, "values": s})

    def overlap(key):
        rs = [i[key] for i in items if i[key]]
        if len(rs) < len(items):
            return None
        lo, hi = max(r["min"] for r in rs), min(r["max"] for r in rs)
        return {"min": lo, "max": hi} if lo <= hi else None

    for key, label in (("o2", "O2 (%)"), ("pressure_atm", "Pressure (atm)"), ("flow_cm_s", "Flow (cm/s)")):
        ov = overlap(key)
        entry = {"attribute": label, "values": {i["accession"]: i[key] for i in items}, "overlap": ov}
        (similarities if ov else differences).append(entry)
    return {"items": items, "similarities": similarities, "differences": differences}


def detail_light(inv: Investigation) -> dict:
    s = summary(inv)
    p = inv.profile or {}
    s.update({
        "measurements": p.get("measurements", []),
        "fuels": p.get("fuels", []),
        "variables": p.get("variables", {}),
        "variable_names": list((p.get("variables") or {}).keys()),
        "constants": p.get("constants", {}),
        "geometry": p.get("geometry"),
        "objective": inv.objective,
        "assumptions": p.get("assumptions", []),
    })
    return s


@app.get("/stats")
def stats(db: Session = Depends(get_session)):
    invs = db.scalars(select(Investigation)).all()
    profiles = [(i, i.profile or {}) for i in invs]
    pillar_counts = {k: sum(1 for _, p in profiles if (p.get("pillars") or {}).get(k, 0) >= 0.5) for k in PILLARS}
    phase = Counter(p.get("fuel_phase", "unknown") for _, p in profiles)
    hardware = Counter(p.get("hardware_family", "Other") for _, p in profiles)
    tiers = Counter(p.get("tier", "supporting") for _, p in profiles)
    timeline = sorted(
        [{"accession": i.accession, "label": i.acronym or i.accession, "start": i.start_year,
          "end": i.end_year or i.start_year, "phase": p.get("fuel_phase")}
         for i, p in profiles if i.start_year],
        key=lambda x: (x["start"], x["label"]))
    max_o2 = max(((p.get("o2") or {}).get("max", 0), i.acronym or i.accession) for i, p in profiles)
    solid_max_o2 = max([(p.get("o2") or {}).get("max", 0) for _, p in profiles if p.get("fuel_phase") == "solid"]
                       or [0])
    return {
        "investigations": len(invs),
        "flight": sum(1 for i in invs if "ground" not in (i.project_type or "").lower()),
        "tables": sum(len(i.tables) for i in invs),
        "test_rows": sum(p.get("test_count", 0) for _, p in profiles),
        "publications": sum(len(i.publications or []) for i in invs),
        "pillars": pillar_counts,
        "phases": dict(phase),
        "hardware": dict(hardware),
        "tiers": dict(tiers),
        "timeline": timeline,
        "max_o2": {"value": max_o2[0], "label": max_o2[1]},
        "solid_max_o2": solid_max_o2,
    }


@app.get("/habitats")
def habitats(db: Session = Depends(get_session)):
    return [
        {c.name: getattr(h, c.name) for c in Habitat.__table__.columns}
        for h in db.scalars(select(Habitat).order_by(Habitat.sort)).all()
    ]


@app.get("/incidents")
def incidents(db: Session = Depends(get_session)):
    return [
        {c.name: getattr(x, c.name) for c in Incident.__table__.columns}
        for x in db.scalars(select(Incident).order_by(Incident.year)).all()
    ]


@app.get("/spinoffs")
def spinoffs(db: Session = Depends(get_session)):
    return [
        {c.name: getattr(x, c.name) for c in Spinoff.__table__.columns}
        for x in db.scalars(select(Spinoff).order_by(Spinoff.year)).all()
    ]


@app.get("/facets")
def facets(db: Session = Depends(get_session)):
    profiles = [i.profile or {} for i in db.scalars(select(Investigation)).all()]
    return {
        "phases": sorted({p.get("fuel_phase") for p in profiles if p.get("fuel_phase")}),
        "hardware": sorted({p.get("hardware_family") for p in profiles if p.get("hardware_family")}),
        "pillars": list(PILLARS),
    }

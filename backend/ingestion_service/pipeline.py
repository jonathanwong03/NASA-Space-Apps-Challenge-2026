"""ETL: PSI (live API or bundled snapshot) -> normalize -> profile -> Postgres."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.config import PSI_SITE_BASE
from common.db import session_scope
from common.models import (
    ExperimentTable,
    Habitat,
    Incident,
    Investigation,
    Spinoff,
    SyncRun,
)
from common.tabular import column_profile, parse_csv

from .curated import HABITATS, INCIDENTS, SPINOFFS
from .profiler import build_profile
from .psi_client import PSIClient

log = logging.getLogger("ingestion")
SNAPSHOT = Path(__file__).parent / "snapshot"


# ------------------------------------------------------------------ normalization


def _year(date: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", date or "")
    return int(m.group(0)) if m else None


def _table_label(acc: str, file_name: str) -> str:
    name = re.sub(r"\.csv$", "", file_name, flags=re.I)
    name = name.replace(f"{acc}_", "").replace("Experimental table_", "").replace("Modeling table_", "")
    return name.strip(" _") or file_name


def normalize(search_src: dict, detail: dict) -> dict:
    acc = detail.get("accession") or search_src.get("Accession")
    pubs = [
        {
            "title": (p.get("title") or "").strip(),
            "authors": (p.get("authorList") or "").strip(),
            "doi": (p.get("doi") or "").strip(),
            "status": ((p.get("status") or {}).get("annotationValue") or ""),
        }
        for p in detail.get("publications", [])
        if p.get("title")
    ]
    contacts = [
        {
            "name": " ".join(x for x in [c.get("firstName", ""), c.get("lastName", "")] if x).strip(),
            "affiliation": c.get("affiliation", ""),
            "role": (c.get("roles") or [{}])[0].get("annotationValue", "") if c.get("roles") else "",
        }
        for c in detail.get("contacts", [])
    ]
    related = [r.strip() for r in re.split(r"[,\s]+", detail.get("related_glds") or
                                           search_src.get("Related Investigations") or "") if r.strip()]
    start = detail.get("investigationStartDate") or search_src.get("Investigation Start Date") or ""
    end = detail.get("investigationEndDate") or search_src.get("Investigation End Date") or ""
    thumb = ""
    if detail.get("images"):
        thumb = f"https://psi.nasa.gov/geode-py/ws/investigations/{acc}/image"
    return {
        "accession": acc,
        "acronym": (detail.get("investigationAcronym") or search_src.get("Acronym") or "").strip(),
        "title": (detail.get("title") or search_src.get("Title") or "").strip(),
        "research_area": detail.get("researchArea") or search_src.get("Research Area") or "",
        "sub_research_area": detail.get("subResearchArea") or search_src.get("SubResearch Area") or "",
        "project_type": detail.get("projectType") or search_src.get("Project Type") or "",
        "flight_platform": detail.get("flightProgram") or search_src.get("Flight Platform") or "",
        "hardware": detail.get("experimentHardware") or "",
        "hardware_link": detail.get("experimentHardwareLink") or "",
        "managing_center": detail.get("managingNasaCenter") or search_src.get("Monitoring Center") or "",
        "start_date": start,
        "end_date": end,
        "start_year": _year(start),
        "end_year": _year(end),
        "doi": detail.get("doi") or "",
        "objective": (detail.get("objective") or search_src.get("Objectives") or "").strip(),
        "hypothesis": (detail.get("hypothesis") or search_src.get("Hypothesis") or "").strip(),
        "approach": (detail.get("approach") or search_src.get("Approach") or "").strip(),
        "research_impacts": (detail.get("researchImpacts") or
                             search_src.get("Research Impacts/Earth Benefits") or "").strip(),
        "keywords": re.sub(r"\s{2,}", "; ", search_src.get("Keywords") or "").strip(),
        "related": related,
        "publications": pubs,
        "contacts": contacts,
        "thumbnail_url": thumb,
        "psi_url": f"{PSI_SITE_BASE}/data/investigations/{acc}",
    }


def _table_files(detail: dict) -> list[tuple[str, str]]:
    out = []
    for kind, key in (("experimental", "experimentalTable"), ("modeling", "modelingTable")):
        for t in detail.get(key) or []:
            if t.get("file_name") and not t.get("restricted"):
                out.append((kind, t["file_name"]))
    return out


# ------------------------------------------------------------------ sources


def load_snapshot() -> list[tuple[dict, dict, list[tuple[str, str, str]]]]:
    search = json.loads((SNAPSHOT / "search.json").read_text(encoding="utf-8"))
    out = []
    for hit in search["hits"]["hits"]:
        src = hit["_source"]
        acc = src["Accession"]
        path = SNAPSHOT / "detail" / f"{acc}.json"
        if not path.exists():
            continue
        detail = json.loads(path.read_text(encoding="utf-8"))
        tables = []
        for kind, fn in _table_files(detail):
            tp = SNAPSHOT / "tables" / fn
            if tp.exists():
                tables.append((kind, fn, tp.read_text(encoding="utf-8")))
        out.append((src, detail, tables))
    return out


def load_live(progress=None) -> list[tuple[dict, dict, list[tuple[str, str, str]]]]:
    client = PSIClient()
    try:
        sources = client.search_investigations()
        out = []
        for i, src in enumerate(sources):
            acc = src["Accession"]
            detail = client.investigation(acc)
            tables = []
            for kind, fn in _table_files(detail):
                try:
                    tables.append((kind, fn, client.file_text(acc, fn)))
                except Exception as e:  # one bad file should not fail the sync
                    log.warning("table %s/%s failed: %s", acc, fn, e)
            out.append((src, detail, tables))
            if progress:
                progress(i + 1, len(sources))
        return out
    finally:
        client.close()


# ------------------------------------------------------------------ load


def upsert(session: Session, records, source: str) -> tuple[int, int]:
    n_tables = 0
    for src, detail, tables in records:
        inv = normalize(src, detail)
        parsed = []
        for kind, fn, text in tables:
            header, rows = parse_csv(text)
            if header:
                parsed.append({"kind": kind, "file_name": fn, "name": _table_label(inv["accession"], fn),
                               "header": header, "rows": rows})
        inv["profile"] = build_profile(inv, parsed)

        obj = session.get(Investigation, inv["accession"])
        if obj is None:
            obj = Investigation(accession=inv["accession"])
            session.add(obj)
        for k, v in inv.items():
            setattr(obj, k, v)
        obj.raw = {"search": src, "detail": detail}
        obj.source = source
        obj.updated_at = datetime.now(timezone.utc)
        session.flush()

        # update tables in place (keyed by file name) so table IDs stay stable across syncs
        existing = {t.file_name: t for t in session.scalars(
            select(ExperimentTable).where(ExperimentTable.accession == obj.accession)).all()}
        for t in parsed:
            row = existing.pop(t["file_name"], None) or ExperimentTable(accession=obj.accession,
                                                                        file_name=t["file_name"])
            row.name, row.kind = t["name"], t["kind"]
            row.columns = column_profile(t["header"], t["rows"])
            row.rows, row.row_count = t["rows"], len(t["rows"])
            session.add(row)
            n_tables += 1
        for stale in existing.values():
            session.delete(stale)
    return len(records), n_tables


def seed_curated(session: Session) -> None:
    for model, rows, key in ((Habitat, HABITATS, "slug"), (Incident, INCIDENTS, "slug"),
                             (Spinoff, SPINOFFS, "slug")):
        for row in rows:
            obj = session.get(model, row[key]) or model(**{key: row[key]})
            for k, v in row.items():
                setattr(obj, k, v)
            session.merge(obj)


def run_sync(mode: str = "auto", progress=None) -> dict:
    """mode: 'live' | 'snapshot' | 'auto' (live, falling back to snapshot)."""
    with session_scope() as s:
        run = SyncRun(mode=mode, status="running")
        s.add(run)
        s.flush()
        run_id = run.id

    used, message = mode, ""
    try:
        if mode == "snapshot":
            records = load_snapshot()
        else:
            try:
                records = load_live(progress)
                used = "live"
                message = f"Fetched {len(records)} investigations from the live NASA PSI API"
            except Exception as e:
                if mode == "live":
                    raise
                log.warning("live PSI sync failed (%s); using bundled snapshot", e)
                records = load_snapshot()
                used = "snapshot"
                message = f"Live PSI API unavailable ({type(e).__name__}); loaded bundled snapshot"
        if used == "snapshot" and not message:
            message = "Loaded bundled PSI snapshot"

        with session_scope() as s:
            n_inv, n_tab = upsert(s, records, used)
            seed_curated(s)
            run = s.get(SyncRun, run_id)
            run.mode, run.status, run.message = used, "ok", message
            run.investigations, run.tables = n_inv, n_tab
            run.finished_at = datetime.now(timezone.utc)
        return {"id": run_id, "mode": used, "status": "ok", "investigations": n_inv, "tables": n_tab,
                "message": message}
    except Exception as e:
        log.exception("sync failed")
        with session_scope() as s:
            run = s.get(SyncRun, run_id)
            run.status, run.message = "error", f"{type(e).__name__}: {e}"
            run.finished_at = datetime.now(timezone.utc)
        return {"id": run_id, "mode": mode, "status": "error", "message": str(e)}


def investigation_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Investigation)) or 0

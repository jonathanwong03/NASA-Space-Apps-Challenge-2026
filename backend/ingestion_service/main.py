"""Ingestion microservice: owns the schema and keeps Postgres in sync with NASA PSI."""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from common.config import PSI_API_BASE
from common.db import Base, engine, session_scope, wait_for_db
from common.models import ExperimentTable, Investigation, SyncRun

from .pipeline import investigation_count, run_sync
from .psi_client import PSIClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ingestion")
logging.getLogger("httpx").setLevel(logging.WARNING)  # don't log presigned S3 URLs

STATE = {"ready": False, "syncing": False, "progress": None}
_lock = threading.Lock()


def _sync_in_background(mode: str):
    def progress(done, total):
        STATE["progress"] = {"done": done, "total": total}

    def worker():
        try:
            run_sync(mode, progress)
        finally:
            STATE["syncing"] = False
            STATE["progress"] = None
            _lock.release()

    if not _lock.acquire(blocking=False):
        return False
    STATE["syncing"] = True
    threading.Thread(target=worker, daemon=True).start()
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(engine)
    with session_scope() as s:
        empty = investigation_count(s) == 0
    if empty:
        log.info("database empty - loading bundled PSI snapshot so the dashboard is usable immediately")
        run_sync("snapshot")
    STATE["ready"] = True
    if os.getenv("SYNC_ON_STARTUP", "true").lower() == "true":
        log.info("starting live sync from NASA PSI API in background")
        _sync_in_background("auto")
    yield


app = FastAPI(title="FireSafe-SI Ingestion Service", version="1.0.0", lifespan=lifespan,
              root_path=os.getenv("ROOT_PATH", ""))


@app.get("/health")
def health():
    if not STATE["ready"]:
        return JSONResponse({"status": "starting"}, status_code=503)
    return {"status": "ok", "service": "ingestion"}


@app.get("/status")
def status():
    with session_scope() as s:
        runs = s.scalars(select(SyncRun).order_by(SyncRun.id.desc()).limit(10)).all()
        n_inv = s.scalar(select(func.count()).select_from(Investigation))
        n_tab = s.scalar(select(func.count()).select_from(ExperimentTable))
        n_rows = s.scalar(select(func.coalesce(func.sum(ExperimentTable.row_count), 0)))
        by_source = dict(s.execute(select(Investigation.source, func.count()).group_by(Investigation.source)).all())
        last_ok = next((r for r in runs if r.status == "ok"), None)
        return {
            "syncing": STATE["syncing"],
            "progress": STATE["progress"],
            "investigations": n_inv,
            "tables": n_tab,
            "test_rows": int(n_rows or 0),
            "by_source": by_source,
            "data_mode": last_ok.mode if last_ok else None,
            "last_sync": last_ok.finished_at.isoformat() if last_ok and last_ok.finished_at else None,
            "psi_api": PSI_API_BASE,
            "runs": [
                {"id": r.id, "mode": r.mode, "status": r.status, "message": r.message,
                 "investigations": r.investigations, "tables": r.tables,
                 "started_at": r.started_at.isoformat() if r.started_at else None,
                 "finished_at": r.finished_at.isoformat() if r.finished_at else None}
                for r in runs
            ],
        }


@app.get("/psi/ping")
def psi_ping():
    c = PSIClient()
    try:
        return {"reachable": c.ping(), "api": PSI_API_BASE}
    finally:
        c.close()


@app.post("/sync")
def sync(mode: str = Query("live", pattern="^(live|snapshot|auto)$")):
    if not _sync_in_background(mode):
        raise HTTPException(409, "A sync is already running")
    return {"started": True, "mode": mode}


@app.get("/sources")
def sources():
    return [
        {"name": "NASA Physical Sciences Informatics (PSI): Combustion Science investigations",
         "url": "https://psi.nasa.gov/physci/repo/search?q=combustion&data_source=psi&data_type=investigation",
         "kind": "NASA dataset (live API)",
         "use": "Investigation metadata, objectives, hypotheses, approach, hardware, publications and the "
                "experimental test-matrix CSVs (fuels, O2, pressure, flow, outcomes)."},
        {"name": "PSI web service (JSON)", "url": f"{PSI_API_BASE}/repo/search?type=investigation",
         "kind": "NASA API", "use": "Live sync endpoint used by this service."},
        {"name": "NASA Glenn Combustion Science",
         "url": "https://www.nasa.gov/glenn/glenn-expertise-space-exploration/physical-sciences-program/combustion-science/",
         "kind": "NASA reference", "use": "Program context for the investigations."},
        {"name": "A Researcher's Guide to Combustion Science",
         "url": "https://www.nasa.gov/missions/station/a-researchers-guide-to-combustion-science/",
         "kind": "NASA reference", "use": "Background on microgravity combustion and fire safety."},
        {"name": "Apollo 1 (NASA OSMA lessons learned)",
         "url": "https://sma.nasa.gov/sma-disciplines/accllp/apollo-1#history", "kind": "NASA history",
         "use": "Incident timeline."},
        {"name": "Apollo 13 (NASA OSMA lessons learned)",
         "url": "https://sma.nasa.gov/sma-disciplines/accllp/apollo-13", "kind": "NASA history",
         "use": "Incident timeline."},
        {"name": "25 Years Ago: Fire Aboard Space Station Mir",
         "url": "https://www.nasa.gov/history/25-years-ago-fire-aboard-space-station-mir/", "kind": "NASA history",
         "use": "Incident timeline."},
        {"name": "NASA Spinoff: Fire Detector", "url": "https://spinoff.nasa.gov/node/9407",
         "kind": "NASA Spinoff", "use": "Earth-benefit applications."},
        {"name": "NASA Spinoff: Firefighter's Air Tanks", "url": "https://spinoff.nasa.gov/node/9582",
         "kind": "NASA Spinoff", "use": "Earth-benefit applications."},
        {"name": "NASA Spinoff: New Technology for the Fire Attire", "url": "https://spinoff.nasa.gov/node/9918",
         "kind": "NASA Spinoff", "use": "Earth-benefit applications."},
        {"name": "NASA Spinoff: Industrial Productivity (ISS fine-water-mist extinguisher valve)",
         "url": "https://spinoff.nasa.gov/node/11065", "kind": "NASA Spinoff", "use": "Earth-benefit applications."},
    ]

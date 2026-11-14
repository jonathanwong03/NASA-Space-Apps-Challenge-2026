"""In-memory view of the catalog for the insights engine (refreshed when the DB changes)."""

from __future__ import annotations

import threading
import time

from sqlalchemy import func, select

from common.db import session_scope
from common.models import Habitat, Incident, Investigation

_cache: dict = {"stamp": None, "checked": 0.0, "data": None}
_lock = threading.Lock()


def _stamp(s):
    return s.execute(select(func.max(Investigation.updated_at), func.count()).select_from(Investigation)).one()


def load() -> dict:
    """Returns {'investigations': [...], 'habitats': {...}, 'incidents': [...]}; cached for 30 s."""
    with _lock:
        now = time.time()
        if _cache["data"] is not None and now - _cache["checked"] < 30:
            return _cache["data"]
        with session_scope() as s:
            stamp = tuple(_stamp(s))
            if _cache["data"] is not None and stamp == _cache["stamp"]:
                _cache["checked"] = now
                return _cache["data"]
            invs = []
            for i in s.scalars(select(Investigation).order_by(Investigation.accession)).all():
                invs.append({
                    "accession": i.accession, "acronym": i.acronym, "title": i.title,
                    "label": i.acronym or i.accession,
                    "sub_research_area": i.sub_research_area, "project_type": i.project_type,
                    "flight_platform": i.flight_platform, "hardware": i.hardware,
                    "objective": i.objective, "hypothesis": i.hypothesis, "approach": i.approach,
                    "research_impacts": i.research_impacts, "keywords": i.keywords,
                    "publications": i.publications or [], "related": i.related or [],
                    "start_year": i.start_year, "end_year": i.end_year, "doi": i.doi,
                    "psi_url": i.psi_url, "profile": i.profile or {},
                    "tables": [{"name": t.name, "rows": t.row_count,
                                "columns": [c["name"] for c in t.columns]} for t in i.tables],
                })
            habitats = {
                h.slug: {c.name: getattr(h, c.name) for c in Habitat.__table__.columns}
                for h in s.scalars(select(Habitat).order_by(Habitat.sort)).all()
            }
            incidents = [
                {c.name: getattr(x, c.name) for c in Incident.__table__.columns}
                for x in s.scalars(select(Incident).order_by(Incident.year)).all()
            ]
        data = {"investigations": invs, "habitats": habitats, "incidents": incidents, "stamp": str(stamp)}
        _cache.update(stamp=stamp, checked=now, data=data)
        return data

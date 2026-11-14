"""Insights (SI) microservice: ranking, gap analysis, search, Q&A and briefs."""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from common.config import CLAUDE_MODEL
from common.db import session_scope, wait_for_db
from common.models import AIBrief

from . import llm
from .engine import extractive_answer, template_brief
from .knowledge import load
from .ranking import WEIGHTS, gaps, rank
from .search import Index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("insights")

@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    yield


app = FastAPI(title="FireSafe-SI Insights Service", version="1.0.0", lifespan=lifespan,
              root_path=os.getenv("ROOT_PATH", ""))
_index: dict = {"stamp": None, "index": None}


def index_for(data) -> Index:
    if _index["stamp"] != data["stamp"]:
        _index.update(stamp=data["stamp"], index=Index(data["investigations"]))
    return _index["index"]


def scenario_or_404(data, slug):
    if slug is None:
        return None
    hab = data["habitats"].get(slug)
    if not hab:
        raise HTTPException(404, f"Unknown scenario '{slug}'")
    return hab


@app.get("/health")
def health():
    return {"status": "ok", "service": "insights"}


@app.get("/status")
def status():
    return {"llm_enabled": llm.enabled(), "model": CLAUDE_MODEL if llm.enabled() else None,
            "engine": "claude" if llm.enabled() else "offline-rules", "weights": WEIGHTS}


@app.get("/scenarios")
def scenarios():
    return list(load()["habitats"].values())


@app.get("/rank")
def ranking(scenario: str = "lunar_base",
            focus: str = Query("all", pattern="^(all|prevention|detection|suppression)$"),
            limit: int | None = None):
    data = load()
    hab = scenario_or_404(data, scenario)
    return {"scenario": hab, "focus": focus, "weights": WEIGHTS,
            "results": rank(data["investigations"], hab, focus, limit)}


@app.get("/gaps")
def coverage_gaps():
    data = load()
    return gaps(data["investigations"], data["habitats"])


@app.get("/recommendations")
def recommendations(scenario: str = "lunar_base"):
    """Top investigations to consult per fire-safety pillar for a scenario."""
    data = load()
    hab = scenario_or_404(data, scenario)
    return {p: rank(data["investigations"], hab, p, 3) for p in ("prevention", "detection", "suppression")}


@app.get("/search")
def search(q: str, k: int = 8):
    data = load()
    return index_for(data).search(q, k)


class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    scenario: str | None = None
    history: list[dict] = Field(default_factory=list)


def sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.post("/ask")
async def ask(body: AskBody):
    data = load()
    hab = scenario_or_404(data, body.scenario)
    ranked = rank(data["investigations"], hab) if hab else []
    idx = index_for(data)
    sources = idx.search(body.question, k=6)

    async def gen():
        yield sse({"type": "meta", "engine": "claude" if llm.enabled() else "offline-rules",
                   "model": CLAUDE_MODEL if llm.enabled() else None, "sources": sources})
        if llm.enabled():
            async for chunk in llm.stream_answer(body.question, data, hab, ranked, body.history):
                yield sse({"type": "text", "text": chunk})
        else:
            text = extractive_answer(body.question, data, hab, ranked, idx)
            for i in range(0, len(text), 120):
                yield sse({"type": "text", "text": text[i:i + 120]})
        yield sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/brief/{accession}")
async def get_brief(accession: str, refresh: bool = False):
    data = load()
    acc = accession.upper()
    inv = next((i for i in data["investigations"] if i["accession"] == acc), None)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    if not llm.enabled():
        return {"accession": acc, "engine": "offline-rules", "model": None, "content": template_brief(inv)}
    with session_scope() as s:
        cached = s.get(AIBrief, acc)
        if cached and not refresh and cached.model == CLAUDE_MODEL:
            return {"accession": acc, "engine": "claude", "model": cached.model, "content": cached.content,
                    "cached": True}
    try:
        content = await llm.brief(acc, data)
    except Exception as e:
        log.warning("brief generation failed for %s: %s", acc, e)
        return {"accession": acc, "engine": "offline-rules", "model": None, "content": template_brief(inv),
                "error": f"Claude unavailable ({type(e).__name__}); showing rule-based brief"}
    with session_scope() as s:
        s.merge(AIBrief(accession=acc, model=CLAUDE_MODEL, content=content))
    return {"accession": acc, "engine": "claude", "model": CLAUDE_MODEL, "content": content, "cached": False}

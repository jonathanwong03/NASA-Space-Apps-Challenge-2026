"""Small dependency-free BM25 search over investigation text, with snippet extraction."""

from __future__ import annotations

import math
import re
from collections import Counter

STOP = set("""a an and are as at be by for from has have in into is it its of on or that the this to was were
which with we our their these those not but can will been than then also using used use such each per
via both between all any more most other over under within""".split())

FIELDS = (("title", 3.0), ("acronym", 3.0), ("keywords", 2.0), ("objective", 1.5), ("hypothesis", 1.0),
          ("approach", 1.0), ("research_impacts", 1.0))


def tokens(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9][a-z0-9\-\*]*", (text or "").lower()):
        if w in STOP or len(w) < 2:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


class Index:
    def __init__(self, investigations: list[dict]):
        self.docs = investigations
        self.tf: list[Counter] = []
        self.len: list[float] = []
        for inv in investigations:
            c = Counter()
            for field, w in FIELDS:
                for t in tokens(inv.get(field) or ""):
                    c[t] += w
            p = inv["profile"]
            extra = " ".join(p.get("fuels", []) + p.get("measurements", []) +
                             [p.get("fuel_phase", ""), p.get("hardware_family", ""), p.get("summary", ""),
                              p.get("primary_pillar", ""), inv.get("sub_research_area") or ""])
            for t in tokens(extra):
                c[t] += 1.5
            self.tf.append(c)
            self.len.append(sum(c.values()))
        self.avg = sum(self.len) / max(len(self.len), 1)
        df = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(self.tf)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, k: int = 8) -> list[dict]:
        q = tokens(query)
        if not q:
            return []
        k1, b = 1.4, 0.75
        scored = []
        for i, c in enumerate(self.tf):
            s = 0.0
            for t in q:
                f = c.get(t, 0.0)
                if not f:
                    continue
                s += self.idf.get(t, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * self.len[i] / self.avg))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        top = scored[0][0] if scored else 1
        out = []
        for s, i in scored[:k]:
            inv = self.docs[i]
            out.append({"accession": inv["accession"], "label": inv["label"], "title": inv["title"],
                        "score": round(s / top, 3), "snippet": snippet(inv, q),
                        "summary": inv["profile"].get("summary", "")})
        return out


def snippet(inv: dict, qtokens: list[str], width: int = 260) -> str:
    text = " ".join(inv.get(f) or "" for f in ("objective", "hypothesis", "approach", "research_impacts"))
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text))
    qs = set(qtokens)
    best = max(sentences, key=lambda s: len(qs & set(tokens(s))), default="")
    return best[:width] + ("..." if len(best) > width else "")

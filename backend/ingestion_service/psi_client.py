"""Client for NASA's Physical Sciences Informatics (PSI) public web services.

PSI's Angular front-end (https://psi.nasa.gov/physci/repo) is backed by a JSON API:

  GET {base}/repo/search?type=investigation&size=N&ffield=Research Area&fvalue=combustion science
  GET {base}/repo/investigations/{accession}
  GET {base}/studies/{accession}/download?file={file_name}&redirect=false   -> presigned S3 URL

No authentication is required for public investigations.
"""

from __future__ import annotations

import httpx

from common.config import PSI_API_BASE

HEADERS = {"User-Agent": "FireSafe-SI/1.0 (NASA Space Apps dashboard)", "Accept": "application/json"}


class PSIClient:
    def __init__(self, base: str = PSI_API_BASE, timeout: float = 45.0):
        self.base = base.rstrip("/")
        self.http = httpx.Client(timeout=timeout, headers=HEADERS, follow_redirects=True)

    def close(self):
        self.http.close()

    def search_investigations(self, research_area: str = "combustion science", size: int = 500) -> list[dict]:
        params = [("type", "investigation"), ("size", str(size)),
                  ("ffield", "Research Area"), ("fvalue", research_area)]
        r = self.http.get(f"{self.base}/repo/search", params=params)
        r.raise_for_status()
        return [h["_source"] for h in r.json()["hits"]["hits"]]

    def investigation(self, accession: str) -> dict:
        r = self.http.get(f"{self.base}/repo/investigations/{accession}")
        r.raise_for_status()
        data = r.json()
        data.pop("added", None)
        data.pop("removed", None)
        return data

    def file_text(self, accession: str, file_name: str) -> str:
        r = self.http.get(f"{self.base}/studies/{accession}/download",
                          params={"file": file_name, "redirect": "false"})
        r.raise_for_status()
        url = r.text.strip().strip('"')
        f = self.http.get(url, headers={"Accept": "*/*"})
        f.raise_for_status()
        return f.content.decode("utf-8", errors="replace")

    def ping(self) -> bool:
        try:
            r = self.http.get(f"{self.base}/repo/filter-options", timeout=10)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

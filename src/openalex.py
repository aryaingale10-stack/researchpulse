"""Small OpenAlex REST client: rate limiting, retries, on-disk cache, and budget tracking.

OpenAlex bills every request against a daily budget (about 1,000 list/group_by calls per
day without a key, 10,000 with a free key). Every response is cached in SQLite, so a re-run
of the pipeline costs nothing.
"""
from __future__ import annotations

import json
import sqlite3
import time
from urllib.parse import urlencode

import requests

from .config import CACHE_PATH, MAX_RPS, OPENALEX_API_KEY, OPENALEX_BASE


class BudgetExhausted(RuntimeError):
    pass


class OpenAlex:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "ResearchPulse (student portfolio project)"
        self.cache = sqlite3.connect(CACHE_PATH)
        self.cache.execute("CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, body TEXT)")
        self.interval = 1.0 / MAX_RPS
        self.last_call = 0.0
        self.calls = 0
        self.cache_hits = 0
        self.remaining = None

    def get(self, path: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{OPENALEX_BASE}{path}?{urlencode(params, safe=':|,!<>*')}"
        row = self.cache.execute("SELECT body FROM cache WHERE url = ?", (url,)).fetchone()
        if row:
            self.cache_hits += 1
            return json.loads(row[0])

        send_params = dict(params)
        if OPENALEX_API_KEY:
            send_params["api_key"] = OPENALEX_API_KEY
        send_url = f"{OPENALEX_BASE}{path}?{urlencode(send_params, safe=':|,!<>*')}"
        for attempt in range(6):
            wait = self.interval - (time.monotonic() - self.last_call)
            if wait > 0:
                time.sleep(wait)
            self.last_call = time.monotonic()
            try:
                r = self.session.get(send_url, timeout=60)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            self.calls += 1
            if "X-RateLimit-Remaining" in r.headers:
                self.remaining = r.headers["X-RateLimit-Remaining"]
            if r.status_code == 429:
                if self.remaining is not None and str(self.remaining).strip() in ("0", "0.0"):
                    raise BudgetExhausted(
                        "OpenAlex daily budget used up. Re-run tomorrow (finished calls are cached), "
                        "or get a free API key at openalex.org and set OPENALEX_API_KEY.")
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            self.cache.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (url, r.text))
            self.cache.commit()
            return r.json()
        raise RuntimeError(f"OpenAlex request kept failing: {url}")

    # ---- helpers ------------------------------------------------------------------------
    def group_by(self, filters: str, group: str) -> list[dict]:
        """Returns [{'key', 'key_display_name', 'count'}, ...] (first page, up to 200 groups)."""
        data = self.get("/works", filter=filters, group_by=group, per_page=200)
        return data.get("group_by") or []

    def count(self, filters: str) -> int:
        data = self.get("/works", filter=filters, per_page=1, select="id")
        return int((data.get("meta") or {}).get("count") or 0)


def short_id(key) -> str:
    """'https://openalex.org/subfields/1702' -> '1702'; 'https://openalex.org/countries/US' -> 'US'."""
    return str(key).rstrip("/").split("/")[-1]

"""Settings and paths for ResearchPulse."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
TABLEAU_DIR = OUTPUT_DIR / "tableau"
DOCS_DIR = ROOT / "docs"
SQL_DIR = ROOT / "sql"
DB_PATH = DATA_DIR / "researchpulse.db"
CACHE_PATH = DATA_DIR / "openalex_cache.db"

OPENALEX_BASE = os.environ.get("OPENALEX_BASE", "https://api.openalex.org")
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "")
# OpenAlex allows 10 req/s without a key (30 with a free key); stay well under it.
MAX_RPS = float(os.environ.get("OPENALEX_MAX_RPS", "5"))

FIRST_YEAR = 2015
LAST_YEAR = 2025          # last complete year; the current year is partial and still being indexed
WORK_TYPES = "article|review"   # peer-reviewed output; preprints excluded to avoid double counting

for d in (DATA_DIR, OUTPUT_DIR, TABLEAU_DIR, DOCS_DIR):
    d.mkdir(parents=True, exist_ok=True)

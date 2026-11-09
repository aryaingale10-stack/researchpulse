"""Data collection from OpenAlex into SQLite.

OpenAlex classifies every work into a 4-level hierarchy: domain > field (26) > subfield (252)
> topic (~4,500). We only need counts, so every call is a cheap `group_by` aggregate instead
of downloading millions of papers.

Stage A (always):
  taxonomy        /subfields                                   2 calls
  field_year      group_by primary_topic.field.id, per year    11 calls  (+ unknown bucket)
  subfield_year   group_by publication_year, per subfield     252 calls
  cross_field     group_by topics.field.id, per field x 3 yrs  78 calls
  focus_cross     group_by topics.field.id, per year           11 calls  (e.g. AI x every field)
  institution     group_by primary_topic.field.id, per year    12 calls
Stage B (after metrics, for the top-N rising subfields only):
  topic_window    group_by primary_topic.id, 2 windows         2 x N calls
  country         group_by authorships.countries, 2 years      2 x N calls
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from .config import FIRST_YEAR, LAST_YEAR, WORK_TYPES
from .openalex import OpenAlex, short_id

YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
CROSS_YEARS = [FIRST_YEAR, (FIRST_YEAR + LAST_YEAR) // 2, LAST_YEAR]
BASE = f"type:{WORK_TYPES}"


def _progress(label, i, n):
    if i == n or i % 25 == 0:
        print(f"    {label}: {i}/{n}")


def taxonomy(api: OpenAlex, con: sqlite3.Connection) -> pd.DataFrame:
    rows = []
    for page in (1, 2):
        data = api.get("/subfields", per_page=200, page=page)
        for s in data.get("results") or []:
            rows.append({
                "subfield_id": short_id(s["id"]), "subfield": s["display_name"],
                "field_id": short_id(s["field"]["id"]), "field": s["field"]["display_name"],
                "domain_id": short_id(s["domain"]["id"]), "domain": s["domain"]["display_name"],
            })
    df = pd.DataFrame(rows).drop_duplicates("subfield_id")
    df.to_sql("subfields", con, if_exists="replace", index=False)
    print(f"  taxonomy: {df['field_id'].nunique()} fields, {len(df)} subfields")
    return df


def field_year(api, con):
    rows, totals = [], []
    for i, y in enumerate(YEARS, 1):
        groups = api.group_by(f"{BASE},publication_year:{y}", "primary_topic.field.id:include_unknown")
        # The unknown bucket comes back as '.../fields/unknown' (or '-111' for numeric keys).
        is_unknown = lambda g: short_id(g["key"]).lower() in ("unknown", "-111", "null", "none")
        unknown = sum(g["count"] for g in groups if is_unknown(g))
        known = [g for g in groups if not is_unknown(g)]
        for g in known:
            rows.append({"field_id": short_id(g["key"]), "year": y, "works": g["count"]})
        totals.append({"year": y, "works": sum(g["count"] for g in known) + unknown,
                       "works_without_topic": unknown})
    pd.DataFrame(rows).to_sql("field_year", con, if_exists="replace", index=False)
    pd.DataFrame(totals).to_sql("year_totals", con, if_exists="replace", index=False)
    print(f"  field x year: {len(rows)} rows")


def subfield_year(api, con, subfields: pd.DataFrame):
    rows = []
    ids = subfields["subfield_id"].tolist()
    for i, sid in enumerate(ids, 1):
        groups = api.group_by(f"{BASE},primary_topic.subfield.id:{sid},publication_year:{FIRST_YEAR}-{LAST_YEAR}",
                              "publication_year")
        found = {int(float(g["key"])): g["count"] for g in groups}
        for y in YEARS:
            rows.append({"subfield_id": sid, "year": y, "works": int(found.get(y, 0))})
        _progress("subfield x year", i, len(ids))
    pd.DataFrame(rows).to_sql("subfield_year", con, if_exists="replace", index=False)


def cross_field(api, con, subfields: pd.DataFrame):
    """For works whose PRIMARY topic is in field X, how many also carry a topic in field Y.
    (A work has up to 3 topics, so this measures field-to-field overlap.)"""
    rows = []
    fields = sorted(subfields["field_id"].unique(), key=int)
    n, i = len(fields) * len(CROSS_YEARS), 0
    for y in CROSS_YEARS:
        for f in fields:
            i += 1
            for g in api.group_by(f"{BASE},primary_topic.field.id:{f},publication_year:{y}", "topics.field.id"):
                rows.append({"year": y, "primary_field_id": f, "other_field_id": short_id(g["key"]),
                             "works": g["count"]})
            _progress("cross-field", i, n)
    pd.DataFrame(rows).to_sql("cross_field", con, if_exists="replace", index=False)


def focus_cross(api, con, focus_subfield: str):
    """Works with ANY topic in the focus subfield (default 1702 = Artificial Intelligence),
    grouped by every field they touch - shows where the focus area is spreading."""
    rows = []
    for y in YEARS:
        for g in api.group_by(f"{BASE},topics.subfield.id:{focus_subfield},publication_year:{y}",
                              "topics.field.id"):
            rows.append({"year": y, "field_id": short_id(g["key"]), "works": g["count"]})
        rows.append({"year": y, "field_id": "_total",
                     "works": api.count(f"{BASE},topics.subfield.id:{focus_subfield},publication_year:{y}")})
    pd.DataFrame(rows).to_sql("focus_cross", con, if_exists="replace", index=False)
    print(f"  focus subfield {focus_subfield}: {len(YEARS)} years collected")


def institution(api, con, name: str):
    data = api.get("/institutions", search=name, per_page=1)
    res = data.get("results") or []
    if not res:
        print(f"  institution '{name}' not found; skipping")
        return None
    inst_id, inst_name = short_id(res[0]["id"]), res[0]["display_name"]
    rows = []
    for y in YEARS:
        for g in api.group_by(f"{BASE},authorships.institutions.lineage:{inst_id},publication_year:{y}",
                              "primary_topic.field.id"):
            rows.append({"year": y, "field_id": short_id(g["key"]), "works": g["count"]})
    pd.DataFrame(rows).to_sql("institution_field_year", con, if_exists="replace", index=False)
    print(f"  institution: {inst_name} ({inst_id})")
    return {"id": inst_id, "name": inst_name}


def topic_windows(api, con, subfield_ids: list[str], early=(2019, 2020), late=(2024, 2025)):
    """Topic counts in two 2-year windows (2-year windows smooth out single-year noise)."""
    rows = []
    for i, sid in enumerate(subfield_ids, 1):
        for label, (a, b) in (("early", early), ("late", late)):
            for g in api.group_by(f"{BASE},primary_topic.subfield.id:{sid},publication_year:{a}-{b}",
                                  "primary_topic.id"):
                rows.append({"subfield_id": sid, "topic_id": short_id(g["key"]), "topic": g["key_display_name"],
                             "window": label, "works": g["count"]})
        _progress("topics (top subfields)", i, len(subfield_ids))
    pd.DataFrame(rows).to_sql("topic_window", con, if_exists="replace", index=False)


def countries(api, con, subfield_ids: list[str], years=(2020, LAST_YEAR)):
    """Country participation: a work counts once for every country among its authors."""
    rows = []
    for i, sid in enumerate(subfield_ids, 1):
        for y in years:
            for g in api.group_by(f"{BASE},primary_topic.subfield.id:{sid},publication_year:{y}",
                                  "authorships.countries"):
                rows.append({"subfield_id": sid, "year": y, "country_code": short_id(g["key"]),
                             "country": g["key_display_name"], "works": g["count"]})
        _progress("countries (top subfields)", i, len(subfield_ids))
    pd.DataFrame(rows).to_sql("country_subfield_year", con, if_exists="replace", index=False)

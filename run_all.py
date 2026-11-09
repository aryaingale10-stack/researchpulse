"""ResearchPulse - run the whole pipeline.

    python run_all.py                                  # defaults: 2015-2025, focus = AI, UNT
    python run_all.py --institution "Texas A&M University" --focus-subfield 2713 --top-n 15

Outputs:
    docs/index.html          interactive dashboard (served by GitHub Pages)
    output/results.json      every number in the dashboard
    output/tableau/*.csv     tidy tables for Tableau / Power BI
    data/researchpulse.db    SQLite database (raw tables + SQL views)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import date

from src import collect
from src.analysis import build
from src.config import (DB_PATH, DOCS_DIR, FIRST_YEAR, LAST_YEAR, OPENALEX_API_KEY, OUTPUT_DIR, WORK_TYPES)
from src.dashboard import write_dashboard
from src.metrics import MIN_WORKS, compute, data_quality
from src.openalex import OpenAlex, BudgetExhausted


def step(n, text):
    print(f"\n[{n}/6] {text}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--focus-subfield", default="1702",
                    help="OpenAlex subfield id to track across fields (default 1702 = Artificial Intelligence)")
    ap.add_argument("--institution", default="University of North Texas",
                    help='institution to profile (use "" to skip)')
    ap.add_argument("--top-n", type=int, default=12, help="rising subfields to drill into (topics, countries)")
    args = ap.parse_args()
    t0 = time.time()
    api = OpenAlex()
    print(f"OpenAlex {'with API key' if OPENALEX_API_KEY else 'without API key (fine: this run needs ~450 calls)'}")

    con = sqlite3.connect(DB_PATH)
    try:
        step(1, "Collect: taxonomy and field/subfield output by year")
        subfields = collect.taxonomy(api, con)
        collect.field_year(api, con)
        collect.subfield_year(api, con, subfields)

        step(2, "Collect: interdisciplinarity and institution profile")
        collect.cross_field(api, con, subfields)
        focus_name = subfields.loc[subfields["subfield_id"] == args.focus_subfield, "subfield"]
        focus = {"id": args.focus_subfield, "name": focus_name.iloc[0] if len(focus_name) else args.focus_subfield}
        collect.focus_cross(api, con, args.focus_subfield)
        inst = collect.institution(api, con, args.institution) if args.institution else None

        step(3, "Compute KPIs: SQL views + log-linear trend fits")
        metrics = compute(con)
        elig = metrics[metrics["eligible"]]
        # Drill into steady risers first (class "Rising"), then fill with the next-highest trends.
        ranked = elig.assign(steady=elig["trend_class"].eq("Rising")).sort_values(
            ["steady", "share_trend_pct"], ascending=[False, False])
        top_ids = ranked["subfield_id"].head(args.top_n).tolist()
        print("  top rising subfields: " + ", ".join(metrics.set_index("subfield_id").loc[top_ids[:5], "subfield"]))

        step(4, f"Drill down into the top {len(top_ids)} rising subfields")
        collect.topic_windows(api, con, top_ids)
        collect.countries(api, con, top_ids)
    except BudgetExhausted as e:
        print(f"\nStopped: {e}")
        return

    step(5, "Data quality checks and analysis")
    quality = data_quality(con)
    print("  " + ", ".join(f"{k}={v}" for k, v in quality.items()))
    analysis = build(con, metrics, top_ids, focus, inst)
    con.close()

    step(6, "Write results and dashboard")
    results = {
        "generated": date.today().isoformat(),
        "params": {"first_year": FIRST_YEAR, "last_year": LAST_YEAR, "work_types": WORK_TYPES,
                   "min_works": MIN_WORKS, "early_window": "2019–20", "late_window": "2024–25",
                   "country_years": [2020, LAST_YEAR], "focus_subfield": args.focus_subfield},
        "api_calls": api.calls + api.cache_hits,
        "quality": quality,
        "analysis": analysis,
    }
    (OUTPUT_DIR / "results.json").write_text(json.dumps(results, indent=2, default=str))
    write_dashboard(results, DOCS_DIR / "index.html")
    print(f"\nDone in {(time.time() - t0) / 60:.1f} min ({api.calls} new API calls, {api.cache_hits} cached). "
          f"Open docs/index.html")


if __name__ == "__main__":
    main()

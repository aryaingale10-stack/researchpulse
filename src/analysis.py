"""Turns the collected tables + metrics into the dashboard data and Tableau-ready CSVs."""
from __future__ import annotations

import sqlite3

import pandas as pd

from .config import FIRST_YEAR, LAST_YEAR, TABLEAU_DIR
from .metrics import MID_YEAR


def q(con, sql) -> pd.DataFrame:
    return pd.read_sql(sql, con)


def recs(df: pd.DataFrame) -> list[dict]:
    return df.where(pd.notna(df), None).to_dict(orient="records")


def build(con: sqlite3.Connection, metrics: pd.DataFrame, top_ids: list[str], focus: dict,
          inst: dict | None) -> dict:
    totals = q(con, "SELECT * FROM year_totals ORDER BY year")
    field_idx = q(con, "SELECT * FROM v_field_index ORDER BY field, year")
    field_change = q(con, f"""
        SELECT field,
               MAX(CASE WHEN year = {FIRST_YEAR} THEN share_pct END) AS share_first,
               MAX(CASE WHEN year = {LAST_YEAR}  THEN share_pct END) AS share_last,
               MAX(CASE WHEN year = {LAST_YEAR}  THEN works END)     AS works_last
        FROM v_field_index GROUP BY field""")
    field_change["share_change_pts"] = (field_change["share_last"] - field_change["share_first"]).round(3)
    field_change = field_change.sort_values("share_change_pts", ascending=False)

    elig = metrics[metrics["eligible"]].copy()
    cols = ["subfield_id", "subfield", "field", "domain", "works_mid", "works_last", "cagr_recent",
            "cagr_prior", "share_cagr", "share_trend_pct", "share_r2", "raw_trend_pct", "trend_class"]
    rising = elig.sort_values("share_trend_pct", ascending=False).head(15)[cols]
    declining = elig.sort_values("share_trend_pct").head(10)[cols]
    elig["acceleration"] = (elig["cagr_recent"] - elig["cagr_prior"]).round(2)
    accelerating = elig[elig["works_mid"] >= 2000].sort_values("acceleration", ascending=False).head(10)[
        cols + ["acceleration"]]
    class_counts = metrics["trend_class"].value_counts().to_dict()

    # Topic drill-down for the top rising subfields
    tw = q(con, "SELECT * FROM topic_window")
    topics = pd.DataFrame()
    if not tw.empty:
        p = tw.pivot_table(index=["subfield_id", "topic_id", "topic"], columns="window", values="works",
                           aggfunc="sum", fill_value=0).reset_index()
        for c in ("early", "late"):
            if c not in p:
                p[c] = 0
        p = p.merge(metrics[["subfield_id", "subfield"]], on="subfield_id")
        p = p[(p["early"] >= 50) | (p["late"] >= 200)]
        p["growth_pct"] = (100 * (p["late"] - p["early"]) / p["early"].where(p["early"] > 0)).round(1)
        p["abs_growth"] = p["late"] - p["early"]
        topics = p.sort_values("abs_growth", ascending=False).head(25)[
            ["subfield", "topic", "early", "late", "abs_growth", "growth_pct"]]

    # Interdisciplinarity
    cross = q(con, "SELECT * FROM v_cross_field")
    cross_last = cross[cross["year"] == LAST_YEAR]
    cf = cross[cross["year"].isin([FIRST_YEAR, LAST_YEAR])].pivot_table(
        index=["primary_field", "other_field"], columns="year", values="pct_of_primary").reset_index()
    cross_growth = pd.DataFrame()
    if FIRST_YEAR in cf and LAST_YEAR in cf:
        cf = cf.rename(columns={FIRST_YEAR: "pct_first", LAST_YEAR: "pct_last"}).dropna()
        cf["change_pts"] = (cf["pct_last"] - cf["pct_first"]).round(2)
        cross_growth = cf.sort_values("change_pts", ascending=False).head(15)

    # Focus subfield (default AI) spreading into other fields
    fc = q(con, "SELECT * FROM focus_cross")
    focus_out = {}
    if not fc.empty:
        names = q(con, "SELECT DISTINCT field_id, field FROM subfields")
        tot = fc[fc["field_id"] == "_total"].set_index("year")["works"]
        f2 = fc[fc["field_id"] != "_total"].merge(names, on="field_id")
        f2["pct_of_focus"] = (100 * f2["works"] / f2["year"].map(tot)).round(2)
        piv = f2.pivot_table(index="field", columns="year", values="pct_of_focus").reset_index()
        own_field = metrics.loc[metrics["subfield_id"] == focus["id"], "field"]
        own_field = own_field.iloc[0] if len(own_field) else None
        piv = piv[piv["field"] != own_field]
        if FIRST_YEAR in piv and LAST_YEAR in piv:
            piv = piv.rename(columns={FIRST_YEAR: "pct_first", LAST_YEAR: "pct_last"})
            piv["change_pts"] = (piv["pct_last"] - piv["pct_first"]).round(2)
            spread = piv.sort_values("pct_last", ascending=False).head(12)[["field", "pct_first", "pct_last", "change_pts"]]
        else:
            spread = pd.DataFrame()
        share = (tot / totals.set_index("year")["works"] * 100).round(3)
        focus_out = {
            "name": focus["name"], "own_field": own_field,
            "works_by_year": [{"year": int(y), "works": int(w), "share_pct": float(share.get(y, 0))}
                              for y, w in tot.items()],
            "spread": recs(spread),
        }
        f2.to_csv(TABLEAU_DIR / "focus_subfield_by_field_year.csv", index=False)

    # Countries in the top rising subfields
    cs = q(con, "SELECT * FROM country_subfield_year")
    country_out = []
    if not cs.empty:
        sy = q(con, "SELECT subfield_id, year, works AS subfield_works FROM subfield_year")
        cs = cs.merge(sy, on=["subfield_id", "year"]).merge(metrics[["subfield_id", "subfield"]], on="subfield_id")
        cs["pct_of_papers"] = (100 * cs["works"] / cs["subfield_works"]).round(1)
        cs.to_csv(TABLEAU_DIR / "countries_top_subfields.csv", index=False)
        for sid in top_ids:
            g = cs[cs["subfield_id"] == sid]
            if g.empty:
                continue
            last = g[g["year"] == LAST_YEAR].sort_values("works", ascending=False).head(6)
            first = g[g["year"] != LAST_YEAR].set_index("country_code")["pct_of_papers"]
            country_out.append({
                "subfield": g["subfield"].iloc[0],
                "countries": [{"country": r.country, "pct_last": r.pct_of_papers,
                               "pct_first": float(first.get(r.country_code, 0.0))} for r in last.itertuples()],
            })

    # Institution
    inst_out = None
    if inst:
        iy = q(con, """SELECT i.year, s.field, i.works FROM institution_field_year i
                       JOIN (SELECT DISTINCT field_id, field FROM subfields) s USING (field_id)""")
        if not iy.empty:
            tot_i = iy.groupby("year")["works"].sum()
            mid = iy[iy["year"] == MID_YEAR].set_index("field")["works"]
            last = iy[iy["year"] == LAST_YEAR].set_index("field")["works"]
            by_field = pd.DataFrame({"works_mid": mid, "works_last": last}).fillna(0).reset_index()
            by_field = by_field.rename(columns={"index": "field"}).sort_values("works_last", ascending=False).head(10)
            inst_out = {**inst, "works_by_year": [{"year": int(y), "works": int(w)} for y, w in tot_i.items()],
                        "by_field": recs(by_field)}
            iy.to_csv(TABLEAU_DIR / "institution_field_year.csv", index=False)

    # Tableau exports
    q(con, "SELECT * FROM v_subfield_year").to_csv(TABLEAU_DIR / "subfield_year.csv", index=False)
    field_idx.to_csv(TABLEAU_DIR / "field_year_index.csv", index=False)
    metrics.to_csv(TABLEAU_DIR / "subfield_metrics.csv", index=False)
    cross.to_csv(TABLEAU_DIR / "cross_field_overlap.csv", index=False)
    if not topics.empty:
        topics.to_csv(TABLEAU_DIR / "rising_topics.csv", index=False)

    return {
        "totals": recs(totals),
        "field_index": recs(field_idx),
        "field_change": recs(field_change),
        "rising": recs(rising), "declining": recs(declining), "accelerating": recs(accelerating),
        "scatter": recs(elig[["subfield", "field", "works_last", "share_trend_pct", "share_r2", "trend_class"]]),
        "class_counts": class_counts,
        "topics": recs(topics),
        "cross_last": recs(cross_last[["primary_field", "other_field", "pct_of_primary"]]),
        "cross_growth": recs(cross_growth),
        "focus": focus_out,
        "countries": country_out,
        "institution": inst_out,
    }

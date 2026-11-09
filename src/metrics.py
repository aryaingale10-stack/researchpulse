"""KPI computation: runs the SQL views, then fits a log-linear trend per subfield.

Why a regression on top of CAGR? A CAGR uses only two years, so one unusual year can swing it.
Fitting log(share) ~ year over all years gives a growth rate that uses every data point, and R^2
says how steady that trend is - which is what separates a real trend from noise.
"""
from __future__ import annotations

import math
import sqlite3

import numpy as np
import pandas as pd

from .config import FIRST_YEAR, LAST_YEAR, SQL_DIR

MID_YEAR = LAST_YEAR - 5
MIN_WORKS = 500          # ignore subfields with fewer works than this in MID_YEAR (too small, too noisy)


def _power(a, b):
    try:
        return None if a is None or b is None else math.pow(a, b)
    except (ValueError, OverflowError):
        return None


def create_views(con: sqlite3.Connection) -> None:
    con.create_function("POWER", 2, _power)  # not built into every SQLite version
    for f in sorted(SQL_DIR.glob("0[1-4]_*.sql")):
        con.executescript(f.read_text().format(first=FIRST_YEAR, mid=MID_YEAR, last=LAST_YEAR))


def trend_fit(df: pd.DataFrame, col: str) -> pd.DataFrame:
    out = []
    for sid, g in df.groupby("subfield_id"):
        g = g[g[col] > 0].sort_values("year")
        if len(g) < 5:
            out.append({"subfield_id": sid, "trend_pct": np.nan, "r2": np.nan})
            continue
        x, y = g["year"].to_numpy(float), np.log(g[col].to_numpy(float))
        slope, intercept = np.polyfit(x, y, 1)
        pred = slope * x + intercept
        ss_res, ss_tot = ((y - pred) ** 2).sum(), ((y - y.mean()) ** 2).sum()
        out.append({"subfield_id": sid, "trend_pct": round(100 * (math.exp(slope) - 1), 2),
                    "r2": round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else 0.0})
    return pd.DataFrame(out)


def classify(row) -> str:
    t, r2 = row["share_trend_pct"], row["share_r2"]
    if pd.isna(t):
        return "Insufficient data"
    if abs(t) <= 3:
        return "Stable"
    if r2 >= 0.6:
        return "Rising" if t > 0 else "Declining"
    return "Volatile"


def compute(con: sqlite3.Connection) -> pd.DataFrame:
    create_views(con)
    kpis = pd.read_sql("SELECT * FROM v_subfield_kpis", con)
    years = pd.read_sql("SELECT subfield_id, year, works, share_per_mille FROM v_subfield_year", con)
    share_fit = trend_fit(years, "share_per_mille").rename(columns={"trend_pct": "share_trend_pct", "r2": "share_r2"})
    raw_fit = trend_fit(years, "works").rename(columns={"trend_pct": "raw_trend_pct", "r2": "raw_r2"})
    k = kpis.merge(share_fit, on="subfield_id").merge(raw_fit, on="subfield_id")
    k["eligible"] = k["works_mid"].fillna(0) >= MIN_WORKS
    k["trend_class"] = k.apply(classify, axis=1)
    k.loc[~k["eligible"], "trend_class"] = "Too small"
    k = k.sort_values("share_trend_pct", ascending=False)
    k.to_sql("subfield_metrics", con, if_exists="replace", index=False)
    return k


def data_quality(con: sqlite3.Connection) -> dict:
    cur = con.execute((SQL_DIR / "05_data_quality.sql").read_text())
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, cur.fetchone()))

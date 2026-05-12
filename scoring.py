from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

# Proximity weights (plan)
PTS_METRO_500M = 25.0
PTS_PARK_400M = 15.0
PTS_WATER_600M = 10.0
VEL_BONUS_CAP = 20.0


def proximity_points(dist_m: float | None, threshold_m: float, points: float) -> float:
    if dist_m is None or math.isnan(dist_m):
        return 0.0
    return points if dist_m <= threshold_m else 0.0


def turnover_ratio(archived: float, active: float) -> float:
    if active <= 0:
        return float("nan")
    return archived / active


def city_average_turnover(turnovers: pd.Series) -> float:
    s = turnovers.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return float("nan")
    return float(s.mean())


def velocity_bonus_points(
    district_turnover: float,
    city_avg: float,
    city_std: float,
) -> float:
    if math.isnan(district_turnover) or math.isnan(city_avg):
        return 0.0
    if district_turnover <= city_avg:
        return 0.0
    excess = district_turnover - city_avg
    denom = city_std if city_std and not math.isnan(city_std) and city_std > 1e-9 else 1.0
    raw = 5.0 * excess / denom
    return float(min(VEL_BONUS_CAP, max(0.0, raw)))


def desirability_score_row(
    dist_m_metro: float | None,
    dist_m_park: float | None,
    dist_m_water: float | None,
    turnover: float,
    city_avg: float,
    city_std: float,
) -> tuple[float, float]:
    p = 0.0
    p += proximity_points(dist_m_metro, 500, PTS_METRO_500M)
    p += proximity_points(dist_m_park, 400, PTS_PARK_400M)
    p += proximity_points(dist_m_water, 600, PTS_WATER_600M)
    vb = velocity_bonus_points(turnover, city_avg, city_std)
    total = min(100.0, p + vb)
    return total, vb


def join_district_stats(
    listings: pd.DataFrame,
    archived_by_district: pd.DataFrame,
) -> pd.DataFrame:
    if listings.empty:
        return listings
    active_counts = (
        listings.groupby("district_key", dropna=False).size().reset_index(name="active_count")
    )
    arch = archived_by_district if not archived_by_district.empty else pd.DataFrame(
        columns=["district_key", "archived_count"]
    )
    stats = active_counts.merge(arch, on="district_key", how="left")
    stats["archived_count"] = stats["archived_count"].fillna(0)
    stats["turnover_ratio"] = stats.apply(
        lambda r: turnover_ratio(float(r["archived_count"]), float(r["active_count"])),
        axis=1,
    )
    city_avg = city_average_turnover(stats["turnover_ratio"])
    tvals = stats["turnover_ratio"].replace([np.inf, -np.inf], np.nan).dropna()
    city_std = float(tvals.std(ddof=0)) if len(tvals) > 1 else float("nan")
    if math.isnan(city_std) or city_std == 0.0:
        city_std = 1.0

    stats["city_avg_turnover"] = city_avg
    stats["city_std_turnover"] = city_std

    merged = listings.merge(
        stats[
            [
                "district_key",
                "active_count",
                "archived_count",
                "turnover_ratio",
                "city_avg_turnover",
                "city_std_turnover",
            ]
        ].rename(
            columns={
                "active_count": "active_count_district",
                "archived_count": "archived_count_district",
            }
        ),
        on="district_key",
        how="left",
    )

    scores: list[float] = []
    vbs: list[float] = []
    for _, row in merged.iterrows():
        sc, vb = desirability_score_row(
            row.get("dist_m_metro"),
            row.get("dist_m_park"),
            row.get("dist_m_water"),
            float(row["turnover_ratio"]) if pd.notna(row["turnover_ratio"]) else float("nan"),
            float(row["city_avg_turnover"]) if pd.notna(row["city_avg_turnover"]) else float("nan"),
            float(row["city_std_turnover"]) if pd.notna(row["city_std_turnover"]) else 1.0,
        )
        scores.append(sc)
        vbs.append(vb)
    merged["desirability_score"] = scores
    merged["velocity_bonus"] = vbs
    return merged


def flag_undervalued(df: pd.DataFrame) -> pd.Series:
    """
    High desirability vs lower price/sqm using IQR on price_per_sqm_usd and
    desirability above median.
    """
    if df.empty:
        return pd.Series(dtype=bool)
    p = df["price_per_sqm_usd"].astype(float)
    d = df["desirability_score"].astype(float)
    q1, q3 = p.quantile(0.25), p.quantile(0.75)
    iqr = q3 - q1
    low_price = p <= (q1 - 0.75 * iqr) if iqr > 0 else p <= p.median()
    high_des = d >= d.median()
    return low_price & high_des

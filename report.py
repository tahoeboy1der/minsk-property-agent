from __future__ import annotations

import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from minsk_agent.scoring import (
    PTS_METRO_500M,
    PTS_PARK_400M,
    PTS_WATER_600M,
    proximity_points,
)
from minsk_agent.scoring import flag_undervalued


def _district_turnover_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["district_key", "turnover_ratio"])
    sub = df.drop_duplicates(subset=["district_key"])[
        ["district_key", "turnover_ratio"]
    ].copy()
    sub = sub.sort_values("turnover_ratio", ascending=False)
    return sub


def build_dashboard(
    df: pd.DataFrame,
    out_html: Path,
    *,
    open_browser: bool = False,
) -> None:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No listing data", xref="paper", yref="paper", x=0.5, y=0.5)
        out_html.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(out_html, include_plotlyjs="cdn", full_html=True)
        if open_browser:
            webbrowser.open(out_html.resolve().as_uri())
        return

    df = df.copy()
    df["undervalued"] = flag_undervalued(df)

    dt = _district_turnover_frame(df)

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "bar"}, {"type": "scatter"}], [{"type": "scatterpolar", "colspan": 2}, None]],
        subplot_titles=(
            "District turnover (archived / active)",
            "Opportunity: price per sqm (USD) vs desirability",
            "Top 5 properties — amenity radar",
            "",
        ),
        vertical_spacing=0.12,
        row_heights=[0.45, 0.55],
    )

    fig.add_trace(
        go.Bar(
            x=dt["district_key"],
            y=dt["turnover_ratio"],
            marker_color="#c0392b",
            name="Turnover",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["price_per_sqm_usd"],
            y=df["desirability_score"],
            mode="markers",
            marker=dict(
                size=10,
                color=np.where(df["undervalued"], "#27ae60", "#3498db"),
                line=dict(width=0.5, color="#2c3e50"),
            ),
            text=df["listing_code"],
            hovertext=df["address"],
            hoverinfo="text+x+y",
            name="Listings",
        ),
        row=1,
        col=2,
    )

    top5 = df.nlargest(min(5, len(df)), "desirability_score")
    categories = [
        "Metro≤500m",
        "Park≤400m",
        "Water≤600m",
        "Velocity bonus",
        "Days on mkt (inv)",
    ]
    for _, row in top5.iterrows():
        dm = row.get("dist_m_metro")
        dp = row.get("dist_m_park")
        dw = row.get("dist_m_water")
        m_pts = proximity_points(dm, 500, PTS_METRO_500M)
        p_pts = proximity_points(dp, 400, PTS_PARK_400M)
        w_pts = proximity_points(dw, 600, PTS_WATER_600M)
        vb = float(row.get("velocity_bonus") or 0)
        dom = row.get("days_on_market")
        inv_dom = max(0.0, 30.0 - float(dom)) if dom is not None and not pd.isna(dom) else 0.0
        rvals = [m_pts, p_pts, w_pts, vb, min(30.0, inv_dom)]
        fig.add_trace(
            go.Scatterpolar(
                r=rvals + [rvals[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=str(row.get("listing_code")),
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        height=950,
        title_text="Minsk region investor report (realt.by)",
        showlegend=True,
        template="plotly_white",
    )
    fig.update_xaxes(title_text="District", row=1, col=1)
    fig.update_yaxes(title_text="Turnover ratio", row=1, col=1)
    fig.update_xaxes(title_text="USD / sqm", row=1, col=2)
    fig.update_yaxes(title_text="Desirability (0–100)", row=1, col=2)

    out_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(out_html, include_plotlyjs="cdn", full_html=True)
    if open_browser:
        webbrowser.open(out_html.resolve().as_uri())

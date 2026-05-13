"""
Streamlit explorer: filter listings by price, size, distances, district, rooms;
map with Folium. Run from project root:

  streamlit run src/minsk_agent/explorer_app.py

Or: minsk-explorer
"""

from __future__ import annotations

import os
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# Default CSV (same as pipeline output)
_DEFAULT_CSV = "property_data_final.csv"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        st.error(f"File not found: {csv_path}")
        st.stop()
    df = pd.read_csv(csv_path)
    for c in ("lat", "lon", "price_usd", "sqm", "dist_m_metro", "dist_m_park", "dist_m_water"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "rooms" in df.columns:
        df["rooms"] = pd.to_numeric(df["rooms"], errors="coerce")
    return df


def _numeric_range(series: pd.Series, fallback: tuple[float, float]) -> tuple[float, float]:
    s = series.dropna()
    if s.empty:
        return fallback
    return float(s.min()), float(s.max())


def main() -> None:
    st.set_page_config(page_title="Minsk listings explorer", layout="wide")
    st.title("Minsk region listings — map and filters")
    st.caption("Uses `property_data_final.csv` from the pipeline (realt.by + OSM distances).")

    root = _project_root()
    default_csv = root / _DEFAULT_CSV
    env_csv = os.getenv("STREAMLIT_DATA_CSV", "").strip()
    initial = Path(env_csv) if env_csv else default_csv
    if not initial.is_absolute():
        initial = (root / initial).resolve() if (root / initial).exists() else Path(initial).resolve()

    with st.sidebar:
        st.header("Data")
        csv_path = st.text_input("CSV path", value=str(initial))
        path = Path(csv_path).expanduser()
        if not path.is_absolute():
            path = (root / path).resolve()
        st.header("Filters")
        df0 = _load_data(path)

        mask = pd.Series(True, index=df0.index)

        if "price_usd" in df0.columns and df0["price_usd"].notna().any():
            lo, hi = _numeric_range(df0["price_usd"], (0.0, 1_000_000.0))
            price = st.slider("Price (USD)", float(lo), float(hi), (float(lo), float(hi)), step=1000.0)
            mask &= df0["price_usd"].between(price[0], price[1], inclusive="both")

        if "sqm" in df0.columns and df0["sqm"].notna().any():
            lo, hi = _numeric_range(df0["sqm"], (20.0, 200.0))
            sqm = st.slider("Area (m²)", float(lo), float(hi), (float(lo), float(hi)), step=1.0)
            mask &= df0["sqm"].between(sqm[0], sqm[1], inclusive="both")

        if "rooms" in df0.columns and df0["rooms"].notna().any():
            rmin, rmax = _numeric_range(df0["rooms"], (1.0, 5.0))
            r_lo = int(max(1, round(rmin)))
            r_hi = int(max(r_lo, round(rmax)))
            rooms = st.slider("Rooms (min–max)", r_lo, r_hi, (r_lo, r_hi))
            mask &= df0["rooms"].between(rooms[0], rooms[1], inclusive="both")

        if "dist_m_metro" in df0.columns and df0["dist_m_metro"].notna().any():
            mx = float(df0["dist_m_metro"].max())
            if not pd.isna(mx) and mx > 0:
                hi = max(mx, 500.0)
                cap = st.slider("Max distance to metro (m)", 0.0, hi, min(5000.0, hi), step=100.0)
                mask &= df0["dist_m_metro"].le(cap) | df0["dist_m_metro"].isna()

        if "dist_m_park" in df0.columns and df0["dist_m_park"].notna().any():
            mx = float(df0["dist_m_park"].max())
            if not pd.isna(mx) and mx > 0:
                hi = max(mx, 500.0)
                cap_p = st.slider("Max distance to park (m)", 0.0, hi, min(8000.0, hi), step=100.0)
                mask &= df0["dist_m_park"].le(cap_p) | df0["dist_m_park"].isna()

        if "dist_m_water" in df0.columns and df0["dist_m_water"].notna().any():
            mx = float(df0["dist_m_water"].max())
            if not pd.isna(mx) and mx > 0:
                hi = max(mx, 500.0)
                cap_w = st.slider("Max distance to water (m)", 0.0, hi, min(15000.0, hi), step=200.0)
                mask &= df0["dist_m_water"].le(cap_w) | df0["dist_m_water"].isna()

        if "desirability_score" in df0.columns and df0["desirability_score"].notna().any():
            lo, hi = _numeric_range(df0["desirability_score"], (0.0, 100.0))
            des = st.slider("Desirability score", float(lo), float(hi), (float(lo), float(hi)), step=1.0)
            mask &= df0["desirability_score"].between(des[0], des[1], inclusive="both")

        if "district_key" in df0.columns:
            opts = sorted(df0["district_key"].dropna().astype(str).unique().tolist())
            pick = st.multiselect("Districts", options=opts, default=opts[: min(8, len(opts))])
            if pick:
                mask &= df0["district_key"].astype(str).isin(pick)

        if "days_on_market" in df0.columns and df0["days_on_market"].notna().any():
            lo, hi = _numeric_range(df0["days_on_market"], (0.0, 365.0))
            dom = st.slider("Days on market", float(lo), float(hi), (float(lo), float(hi)), step=1.0)
            mask &= df0["days_on_market"].between(dom[0], dom[1], inclusive="both")

    df = df0.loc[mask].copy()
    st.subheader(f"Showing {len(df)} of {len(df0)} listings")

    col_map, col_tbl = st.columns([1.1, 1.0])

    with col_map:
        st.subheader("Map")
        map_df = df.dropna(subset=["lat", "lon"])
        if map_df.empty:
            st.warning("No rows with valid coordinates in the current filter.")
        else:
            center_lat = float(map_df["lat"].median())
            center_lon = float(map_df["lon"].median())
            m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")
            cluster = MarkerCluster().add_to(m)
            for _, row in map_df.iterrows():
                price = row.get("price_usd")
                ps = row.get("price_per_sqm_usd")
                dm = row.get("dist_m_metro")
                title = str(row.get("title", ""))[:80]
                addr = str(row.get("address", ""))[:120]
                link = str(row.get("listing_url", ""))
                tip = f"<b>{title}</b><br>{addr}<br>USD {price:,.0f}" if pd.notna(price) else f"<b>{title}</b><br>{addr}"
                if pd.notna(ps):
                    tip += f"<br>${ps:,.0f}/m²"
                if pd.notna(dm):
                    tip += f"<br>Metro ~{dm:,.0f} m"
                if link:
                    tip += f'<br><a href="{link}" target="_blank">Open listing</a>'
                folium.CircleMarker(
                    location=[float(row["lat"]), float(row["lon"])],
                    radius=6,
                    color="#2980b9",
                    fill=True,
                    fill_opacity=0.75,
                    popup=folium.Popup(tip, max_width=320),
                ).add_to(cluster)
            sw = [float(map_df["lat"].min()), float(map_df["lon"].min())]
            ne = [float(map_df["lat"].max()), float(map_df["lon"].max())]
            m.fit_bounds([sw, ne], padding=(24, 24))
            st_folium(m, width=None, height=520, returned_objects=[])

    with col_tbl:
        st.subheader("Table")
        show_cols = [
            c
            for c in [
                "listing_code",
                "district_key",
                "price_usd",
                "price_per_sqm_usd",
                "sqm",
                "rooms",
                "dist_m_metro",
                "dist_m_park",
                "desirability_score",
                "days_on_market",
                "address",
                "listing_url",
            ]
            if c in df.columns
        ]
        st.dataframe(
            df[show_cols],
            width="stretch",
            hide_index=True,
        )


if __name__ == "__main__":
    main()

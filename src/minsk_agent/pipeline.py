from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from minsk_agent.archived import load_archived_by_district
from minsk_agent.config import Settings, load_settings
from minsk_agent.fx import fetch_byn_per_usd
from minsk_agent.geocode import geocode_missing_coords
from minsk_agent.osm_overpass import enrich_distances, fetch_minsk_osm_features
from minsk_agent.report import build_dashboard
from minsk_agent.scoring import join_district_stats
from minsk_agent.scrape_realt import scrape_active_listings
from minsk_agent.schema import FINAL_COLUMNS

LOG = logging.getLogger(__name__)


def run_from_dataframe(
    listings: pd.DataFrame,
    settings: Settings,
    *,
    fx_byn_per_usd: float,
    archived_by_district: pd.DataFrame,
) -> pd.DataFrame:
    if listings.empty:
        return pd.DataFrame(columns=FINAL_COLUMNS)
    listings = geocode_missing_coords(
        listings,
        user_agent=settings.nominatim_user_agent,
        cache_path=settings.geocode_cache_path,
    )
    osm = fetch_minsk_osm_features(settings.overpass_url, user_agent=settings.nominatim_user_agent)
    dist_m_metro: list[float | None] = []
    dist_m_park: list[float | None] = []
    dist_m_water: list[float | None] = []
    for _, row in listings.iterrows():
        lat, lon = row.get("lat"), row.get("lon")
        if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
            dist_m_metro.append(None)
            dist_m_park.append(None)
            dist_m_water.append(None)
            continue
        dm, dp, dw = enrich_distances(float(lat), float(lon), osm)
        dist_m_metro.append(dm)
        dist_m_park.append(dp)
        dist_m_water.append(dw)
    listings = listings.copy()
    listings["dist_m_metro"] = dist_m_metro
    listings["dist_m_park"] = dist_m_park
    listings["dist_m_water"] = dist_m_water

    scored = join_district_stats(listings, archived_by_district)
    if "city_std_turnover" in scored.columns:
        scored = scored.drop(columns=["city_std_turnover"])

    scored["fx_rate_used"] = float(fx_byn_per_usd)

    for col in FINAL_COLUMNS:
        if col not in scored.columns:
            scored[col] = None
    scored = scored[FINAL_COLUMNS]
    return scored


def run_pipeline(
    *,
    fixture_path: Path | None = None,
    open_browser: bool | None = None,
) -> tuple[pd.DataFrame, Settings]:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    fx = fetch_byn_per_usd()

    if fixture_path and fixture_path.exists():
        LOG.info("Loading fixture listings from %s", fixture_path)
        listings = pd.read_csv(fixture_path)
    else:
        listings = scrape_active_listings(settings, fx_byn_per_usd=fx)

    archived = load_archived_by_district(settings.archived_district_csv)
    final_df = run_from_dataframe(listings, settings, fx_byn_per_usd=fx, archived_by_district=archived)

    settings.output_csv.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(settings.output_csv, index=False)
    LOG.info("Wrote %s (%s rows)", settings.output_csv, len(final_df))

    show = settings.show_dashboard if open_browser is None else open_browser
    build_dashboard(final_df, settings.output_html, open_browser=show)
    LOG.info("Wrote %s", settings.output_html)
    if show:
        LOG.info("Opened dashboard in your default browser")
    return final_df, settings

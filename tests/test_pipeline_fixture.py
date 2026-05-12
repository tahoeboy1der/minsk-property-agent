from __future__ import annotations

from pathlib import Path

import pandas as pd

from minsk_agent.osm_overpass import OsmFeature
from minsk_agent.pipeline import run_from_dataframe, run_pipeline
from minsk_agent.config import load_settings


def test_run_from_dataframe_with_osm_stub(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "minsk_agent.pipeline.fetch_minsk_osm_features",
        lambda url, user_agent="", **kwargs: {
            "metro": [OsmFeature("metro", 53.915, 27.575)],
            "park": [OsmFeature("park", 53.9155, 27.5755)],
            "water": [OsmFeature("water", 53.914, 27.574)],
        },
    )
    root = Path(__file__).resolve().parents[1]
    listings = pd.read_csv(root / "tests" / "fixtures" / "listings.csv")
    archived = pd.read_csv(root / "data" / "archived_by_district.csv")
    settings = load_settings()
    settings.geocode_cache_path = tmp_path / "gc.sqlite"
    settings.output_csv = tmp_path / "p.csv"
    settings.output_html = tmp_path / "r.html"
    out = run_from_dataframe(listings, settings, fx_byn_per_usd=3.27, archived_by_district=archived)
    assert len(out) == 3
    assert out["dist_m_metro"].iloc[0] < 500
    assert (out["desirability_score"] >= 0).all() and (out["desirability_score"] <= 100).all()


def test_cli_fixture_writes_outputs(monkeypatch, tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setenv("OUTPUT_CSV", str(tmp_path / "out.csv"))
    monkeypatch.setenv("OUTPUT_HTML", str(tmp_path / "out.html"))
    monkeypatch.setenv("GEOCODE_CACHE_PATH", str(tmp_path / "gc.sqlite"))
    monkeypatch.setenv("USE_PLAYWRIGHT", "0")
    monkeypatch.setattr(
        "minsk_agent.pipeline.fetch_minsk_osm_features",
        lambda url, user_agent="", **kwargs: {
            "metro": [OsmFeature("metro", 53.91, 27.57)],
            "park": [OsmFeature("park", 53.92, 27.58)],
            "water": [OsmFeature("water", 53.9, 27.56)],
        },
    )
    monkeypatch.setattr("minsk_agent.pipeline.fetch_byn_per_usd", lambda on_date=None: 3.27)
    run_pipeline(fixture_path=root / "tests" / "fixtures" / "listings.csv")
    assert (tmp_path / "out.csv").exists()
    assert (tmp_path / "out.html").exists()

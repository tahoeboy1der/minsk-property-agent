from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    use_playwright: bool
    headless: bool
    request_delay_sec: float
    max_listing_pages: int
    realt_active_base_url: str
    archived_district_csv: Path | None
    nominatim_user_agent: str
    overpass_url: str
    output_csv: Path
    output_html: Path
    geocode_cache_path: Path
    show_dashboard: bool


def load_settings() -> Settings:
    load_dotenv(_project_root() / ".env", override=False)
    root = _project_root()

    archived_env = os.getenv("ARCHIVED_DISTRICT_CSV", "").strip()
    default_arch = root / "data" / "archived_by_district.csv"
    if archived_env:
        p = Path(archived_env)
        archived_path = p if p.is_absolute() else (root / p)
        if not archived_path.exists():
            archived_path = None
    elif default_arch.exists():
        archived_path = default_arch
    else:
        archived_path = None

    return Settings(
        use_playwright=os.getenv("USE_PLAYWRIGHT", "1").strip() in ("1", "true", "True", "yes"),
        headless=os.getenv("HEADLESS", "1").strip() in ("1", "true", "True", "yes"),
        request_delay_sec=float(os.getenv("REQUEST_DELAY_SEC", "1.5")),
        max_listing_pages=int(os.getenv("MAX_LISTING_PAGES", "3")),
        realt_active_base_url=os.getenv(
            "REALT_ACTIVE_BASE_URL", "https://realt.by/sale/flats/minskij-rajon/"
        ).strip(),
        archived_district_csv=archived_path,
        nominatim_user_agent=os.getenv(
            "NOMINATIM_USER_AGENT",
            "MinskPropertyAgent/1.0 (please set NOMINATIM_USER_AGENT in .env)",
        ).strip(),
        overpass_url=os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter").strip(),
        output_csv=Path(os.getenv("OUTPUT_CSV", "property_data_final.csv")).resolve(),
        output_html=Path(os.getenv("OUTPUT_HTML", "minsk_investor_report.html")).resolve(),
        geocode_cache_path=Path(os.getenv("GEOCODE_CACHE_PATH", "data/geocode_cache.sqlite"))
        .resolve(),
        show_dashboard=os.getenv("SHOW_DASHBOARD", "0").strip() in ("1", "true", "True", "yes"),
    )

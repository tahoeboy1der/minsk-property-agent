from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

LOG = logging.getLogger(__name__)


def _normalize_address(s: str) -> str:
    return " ".join(s.split()).strip().lower()


class GeocodeCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS geocode (addr TEXT PRIMARY KEY, lat REAL, lon REAL)"
        )
        self._conn.commit()

    def get(self, addr: str) -> tuple[float, float] | None:
        key = _normalize_address(addr)
        cur = self._conn.execute("SELECT lat, lon FROM geocode WHERE addr = ?", (key,))
        row = cur.fetchone()
        if row:
            return float(row[0]), float(row[1])
        return None

    def put(self, addr: str, lat: float, lon: float) -> None:
        key = _normalize_address(addr)
        self._conn.execute(
            "INSERT OR REPLACE INTO geocode(addr, lat, lon) VALUES (?,?,?)",
            (key, lat, lon),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def geocode_missing_coords(
    df: pd.DataFrame,
    *,
    user_agent: str,
    cache_path: Path,
    country_bias: str = "Belarus",
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    cache = GeocodeCache(cache_path)
    geolocator = Nominatim(user_agent=user_agent, timeout=20)
    rate_limited = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

    for i, row in out.iterrows():
        lat, lon = row.get("lat"), row.get("lon")
        if lat is not None and lon is not None and pd.notna(lat) and pd.notna(lon):
            continue
        addr = str(row.get("address") or "").strip()
        if not addr:
            continue
        q = f"{addr}, {country_bias}"
        cached = cache.get(q)
        if cached:
            out.at[i, "lat"], out.at[i, "lon"] = cached[0], cached[1]
            continue
        try:
            loc = rate_limited(q)
            time.sleep(0.05)
        except Exception as e:
            LOG.warning("Geocode failed for %s: %s", q, e)
            continue
        if loc:
            la, lo = float(loc.latitude), float(loc.longitude)
            out.at[i, "lat"], out.at[i, "lon"] = la, lo
            cache.put(q, la, lo)
    cache.close()
    return out

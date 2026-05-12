from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

LOG = logging.getLogger(__name__)

# Minsk metro area bbox (south, west, north, east) for Overpass
MINSK_BBOX = (53.75, 27.35, 53.98, 27.75)

# overpass-api.de often returns 406 for default python-requests User-Agent; use a descriptive UA.
_OVERPASS_FALLBACKS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


@dataclass
class OsmFeature:
    kind: str
    lat: float
    lon: float


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
def overpass_query(
    overpass_url: str,
    ql: str,
    *,
    user_agent: str,
    timeout: int = 180,
) -> dict[str, Any]:
    headers = {
        "User-Agent": user_agent,
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    r = requests.post(overpass_url, data={"data": ql}, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _centroid_coords(elem: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in elem and "lon" in elem:
        return float(elem["lat"]), float(elem["lon"])
    center = elem.get("center")
    if center:
        return float(center["lat"]), float(center["lon"])
    return None


def fetch_minsk_osm_features(overpass_url: str, *, user_agent: str) -> dict[str, list[OsmFeature]]:
    south, west, north, east = MINSK_BBOX
    ql = f"""
    [out:json][timeout:120];
    (
      node["railway"="station"]({south},{west},{north},{east});
      way["railway"="station"]({south},{west},{north},{east});
      node["leisure"="park"]({south},{west},{north},{east});
      way["leisure"="park"]({south},{west},{north},{east});
      node["natural"="water"]({south},{west},{north},{east});
      way["natural"="water"]({south},{west},{north},{east});
    );
    out center;
    """
    urls_to_try: list[str] = []
    for u in (overpass_url,) + _OVERPASS_FALLBACKS:
        if u not in urls_to_try:
            urls_to_try.append(u)

    last_exc: Exception | None = None
    data: dict[str, Any] | None = None
    for url in urls_to_try:
        try:
            data = overpass_query(url, ql, user_agent=user_agent)
            if url != overpass_url:
                LOG.warning("Overpass succeeded using mirror %s (primary was unavailable)", url)
            break
        except requests.HTTPError as e:
            last_exc = e
            code = e.response.status_code if e.response is not None else 0
            if code in (406, 429, 502, 503, 504):
                LOG.warning(
                    "Overpass HTTP %s from %s — trying next endpoint if any",
                    code,
                    url,
                )
                continue
            raise
    if data is None and last_exc is not None:
        raise last_exc
    assert data is not None
    elements = data.get("elements") or []
    metros: list[OsmFeature] = []
    parks: list[OsmFeature] = []
    waters: list[OsmFeature] = []
    for el in elements:
        tags = el.get("tags") or {}
        c = _centroid_coords(el)
        if not c:
            continue
        lat, lon = c
        if tags.get("railway") == "station":
            metros.append(OsmFeature("metro", lat, lon))
        if tags.get("leisure") == "park":
            parks.append(OsmFeature("park", lat, lon))
        if tags.get("natural") == "water":
            waters.append(OsmFeature("water", lat, lon))
    LOG.info(
        "OSM: %s metro stations, %s parks, %s water features in bbox",
        len(metros),
        len(parks),
        len(waters),
    )
    return {"metro": metros, "park": parks, "water": waters}


def min_distance_m(lat: float, lon: float, feats: list[OsmFeature]) -> float | None:
    if not feats:
        return None
    return min(haversine_m(lat, lon, f.lat, f.lon) for f in feats)


def enrich_distances(
    lat: float,
    lon: float,
    osm: dict[str, list[OsmFeature]],
) -> tuple[float | None, float | None, float | None]:
    return (
        min_distance_m(lat, lon, osm["metro"]),
        min_distance_m(lat, lon, osm["park"]),
        min_distance_m(lat, lon, osm["water"]),
    )

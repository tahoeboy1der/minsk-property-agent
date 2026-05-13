from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pandas as pd

from minsk_agent.config import Settings
from minsk_agent.fetch_realt import fetch_listing_index_html, objects_from_html

LOG = logging.getLogger(__name__)

ISO_CURRENCY_NUM = {840: "USD", 933: "BYN", 978: "EUR", 643: "RUB"}


def _district_key(o: dict[str, Any]) -> str:
    town = (o.get("townName") or "").strip()
    sd = (o.get("stateDistrictName") or "").strip()
    if town:
        return town
    return sd or "unknown"


def _listing_url(code: int | str) -> str:
    return f"https://realt.by/sale-flats/object/{code}/"


def _parse_ts(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def object_to_record(
    o: dict[str, Any],
    *,
    status: str,
    fx_byn_per_usd: float,
    scraped_at: dt.datetime,
) -> dict[str, Any]:
    code = o.get("code")
    rates = o.get("priceRates") or {}
    rates_m2 = o.get("priceRatesPerM2") or {}
    cur_num = int(o.get("priceCurrency") or 0)
    cur_iso = ISO_CURRENCY_NUM.get(cur_num, str(cur_num))

    price_usd: float | None = None
    fx_used: float | None = None
    if rates.get("840") is not None:
        price_usd = float(rates["840"])
    elif cur_num == 933:
        raw = float(o.get("price") or 0)
        price_usd = raw / fx_byn_per_usd
        fx_used = fx_byn_per_usd
    elif cur_num == 840:
        price_usd = float(o.get("price") or 0)

    byn_val = rates.get("933")
    price_byn: float | None = float(byn_val) if byn_val is not None else None

    sqm = o.get("areaTotal") or o.get("areaMin") or o.get("areaMax")
    sqm_f = float(sqm) if sqm is not None else None

    ppm_usd = rates_m2.get("840")
    price_per_sqm_usd: float | None = float(ppm_usd) if ppm_usd is not None else None
    if price_per_sqm_usd is None and price_usd is not None and sqm_f and sqm_f > 0:
        price_per_sqm_usd = price_usd / sqm_f

    loc = o.get("location") or []
    lon = float(loc[0]) if len(loc) >= 2 else None
    lat = float(loc[1]) if len(loc) >= 2 else None

    pub = _parse_ts(o.get("createdAt"))
    upd = _parse_ts(o.get("updatedAt"))
    today = dt.datetime.now(dt.timezone.utc).astimezone()
    dom = None
    if pub:
        dom = (today.date() - pub.astimezone().date()).days

    return {
        "listing_code": int(code) if code is not None else None,
        "listing_url": _listing_url(code) if code else "",
        "source": "realt.by",
        "status": status,
        "title": o.get("title") or "",
        "address": o.get("address") or "",
        "district_key": _district_key(o),
        "town_name": o.get("townName") or "",
        "state_district_name": o.get("stateDistrictName") or "",
        "state_region_name": o.get("stateRegionName") or "",
        "sqm": sqm_f,
        "rooms": float(o["rooms"]) if o.get("rooms") is not None else None,
        "storey": float(o["storey"]) if o.get("storey") is not None else None,
        "storeys": float(o["storeys"]) if o.get("storeys") is not None else None,
        "price_raw": o.get("price"),
        "price_currency_iso": cur_iso,
        "price_byn": price_byn,
        "price_usd": price_usd,
        "price_per_sqm_usd": price_per_sqm_usd,
        "fx_rate_used": fx_used if fx_used is not None else float("nan"),
        "published_at": pub.isoformat() if pub else "",
        "updated_at": upd.isoformat() if upd else "",
        "published_at_raw": o.get("createdAt") or "",
        "updated_at_raw": o.get("updatedAt") or "",
        "days_on_market": dom,
        "lon": lon,
        "lat": lat,
        "scraped_at": scraped_at.isoformat(),
    }


def _with_page(url: str, page: int) -> str:
    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    q["page"] = str(page)
    new_q = urlencode(q)
    return urlunparse(parsed._replace(query=new_q))


def scrape_active_listings(settings: Settings, fx_byn_per_usd: float) -> pd.DataFrame:
    base = settings.realt_active_base_url
    ua = settings.nominatim_user_agent
    rows: list[dict[str, Any]] = []
    scraped_at = dt.datetime.now(dt.timezone.utc)

    first_html = fetch_listing_index_html(
        base,
        user_agent=ua,
        use_playwright=settings.use_playwright,
        headless=settings.headless,
    )
    objs, pag = objects_from_html(first_html)
    total = int(pag.get("totalCount") or 0)
    page_size = int(pag.get("pageSize") or len(objs) or 30)
    max_pages = settings.max_listing_pages
    n_pages = min(max_pages, (total + page_size - 1) // page_size if page_size else max_pages)
    n_pages = max(1, n_pages)

    LOG.info("Active listings: totalCount=%s scraping up to %s pages", total, n_pages)

    for page in range(1, n_pages + 1):
        if page == 1:
            page_objs = objs
        else:
            time.sleep(settings.request_delay_sec)
            url = _with_page(base, page)
            html = fetch_listing_index_html(
                url,
                user_agent=ua,
                use_playwright=settings.use_playwright,
                headless=settings.headless,
            )
            page_objs, _ = objects_from_html(html)
        for o in page_objs:
            rows.append(
                object_to_record(
                    o, status="active", fx_byn_per_usd=fx_byn_per_usd, scraped_at=scraped_at
                )
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(subset=["listing_code"])
    return df


def active_counts_by_district(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["district_key", "active_count"])
    g = df.groupby("district_key", dropna=False).size().reset_index(name="active_count")
    return g

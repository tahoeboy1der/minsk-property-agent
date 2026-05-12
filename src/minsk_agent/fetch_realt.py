from __future__ import annotations

import json
import re
import time
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>',
    re.DOTALL,
)


def parse_next_data(html: str) -> dict[str, Any]:
    m = _NEXT_DATA_RE.search(html)
    if not m:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>([^<]+)</script>', html)
    if not m:
        raise ValueError("No __NEXT_DATA__ JSON found in HTML")
    return json.loads(m.group(1))


def page_props(html: str) -> dict[str, Any]:
    data = parse_next_data(html)
    return data["props"]["pageProps"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def fetch_html_requests(url: str, user_agent: str) -> str:
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml",
    }
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    return r.text


def fetch_html_playwright(url: str, user_agent: str, *, headless: bool) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=user_agent,
            locale="ru-BY",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(1500)
        html = page.content()
        context.close()
        browser.close()
    return html


def fetch_listing_index_html(
    url: str, *, user_agent: str, use_playwright: bool, headless: bool
) -> str:
    if use_playwright:
        return fetch_html_playwright(url, user_agent, headless=headless)
    return fetch_html_requests(url, user_agent)


def objects_from_html(html: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pp = page_props(html)
    objs = pp.get("objects") or []
    pag = pp.get("pagination") or {}
    return objs, pag

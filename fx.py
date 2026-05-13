from __future__ import annotations

import datetime as dt
import json
import urllib.request

from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def fetch_byn_per_usd(on_date: dt.date | None = None) -> float:
    """
    Official NBRB rate: BYN per 1 USD (Cur_ID 431).
    https://api.nbrb.by/exrates/rates/431
    """
    d = on_date or dt.date.today()
    qs = f"https://api.nbrb.by/exrates/rates/431?parammode=0&ondate={d.isoformat()}"
    req = urllib.request.Request(qs, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return float(data["Cur_OfficialRate"])

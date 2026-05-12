from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOG = logging.getLogger(__name__)


def load_archived_by_district(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        if path:
            LOG.warning("Archived district CSV not found: %s — turnover_ratio will be incomplete", path)
        return pd.DataFrame(columns=["district_key", "archived_count"])
    df = pd.read_csv(path)
    if "district_key" not in df.columns or "archived_count" not in df.columns:
        raise ValueError(f"CSV {path} must have columns district_key,archived_count")
    return df[["district_key", "archived_count"]].copy()

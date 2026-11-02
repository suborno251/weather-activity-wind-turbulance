"""Elexon BMRS API client and data refresh pipeline."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import requests

from config import (
    ACTUALS_CSV,
    BASE_URL,
    DATA_DIR,
    FETCH_CHUNK_DAYS,
    FETCH_PUBLISH_FROM,
    FORECASTS_CSV,
    SCOPE_END,
    SCOPE_START,
)


def _stream(dataset: str, params: dict) -> list[dict]:
    r = requests.get(
        f"{BASE_URL}/datasets/{dataset}/stream",
        params=params,
        timeout=90,
        headers={"Accept": "application/json"},
    )
    r.raise_for_status()
    payload = r.json()
    return payload["data"] if isinstance(payload, dict) else payload


def _windows(start: datetime, end: datetime, days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt


def refresh_data() -> None:
    """Download wind actuals (FUELHH) and forecasts (WINDFOR) and cache them as CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    scope_from = datetime.combine(SCOPE_START, datetime.min.time())
    scope_to = datetime.combine(SCOPE_END + timedelta(days=1), datetime.min.time())

    act = []
    for a, b in _windows(scope_from, scope_to, 7):
        act += _stream("FUELHH", {
            "settlementDateFrom": a.date().isoformat(),
            "settlementDateTo": (b - timedelta(days=1)).date().isoformat(),
            "fuelType": ["WIND"],
        })
    a_df = pd.DataFrame(act)
    a_df = a_df[a_df["fuelType"] == "WIND"]
    a_df["start_time"] = pd.to_datetime(a_df["startTime"], utc=True)
    a_df = a_df.rename(columns={"generation": "actual"})[["start_time", "actual"]]
    a_df.drop_duplicates("start_time", keep="last").to_csv(ACTUALS_CSV, index=False)

    fc = []
    for a, b in _windows(FETCH_PUBLISH_FROM, scope_to, FETCH_CHUNK_DAYS):
        fc += _stream("WINDFOR", {
            "publishDateTimeFrom": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": b.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    f_df = pd.DataFrame(fc)
    f_df["start_time"] = pd.to_datetime(f_df["startTime"], utc=True)
    f_df["publish_time"] = pd.to_datetime(f_df["publishTime"], utc=True)
    f_df = f_df.rename(columns={"generation": "forecast"})[["start_time", "publish_time", "forecast"]]
    f_df.drop_duplicates(["start_time", "publish_time"]).to_csv(FORECASTS_CSV, index=False)

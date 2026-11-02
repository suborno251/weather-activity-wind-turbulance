"""Analytical algorithms, cutoff snapshot filtering, and accuracy calculations."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import HTTPException

from config import (
    ACTUALS_CSV,
    FORECASTS_CSV,
    LONDON,
    SCOPE_END,
    SCOPE_START,
)
from services.elexon import refresh_data


@lru_cache(maxsize=1)
def load_store() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load cached CSVs or refresh from Elexon BMRS if files are absent."""
    if not (ACTUALS_CSV.exists() and FORECASTS_CSV.exists()):
        try:
            refresh_data()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(503, f"No cached data and Elexon fetch failed: {exc}") from exc
    actuals = pd.read_csv(ACTUALS_CSV, parse_dates=["start_time"])
    fc = pd.read_csv(FORECASTS_CSV, parse_dates=["start_time", "publish_time"])
    for df, cols in ((actuals, ["start_time"]), (fc, ["start_time", "publish_time"])):
        for c in cols:
            df[c] = pd.to_datetime(df[c], utc=True)
    local = fc["start_time"].dt.tz_convert(LONDON)
    fc["delivery_midnight"] = local.dt.normalize()
    fc = fc[(local.dt.date >= SCOPE_START) & (local.dt.date <= SCOPE_END)].reset_index(drop=True)
    return actuals, fc


def parse_cutoff(cutoff: str) -> tuple[int, int]:
    """Validate and parse HH:MM cutoff string."""
    try:
        h, m = cutoff.split(":")
        h, m = int(h), int(m)
        assert 0 <= h < 24 and 0 <= m < 60
        return h, m
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, "cutoff must be HH:MM (24h)") from exc


@lru_cache(maxsize=64)
def latest_before_cutoff(cutoff: str) -> pd.DataFrame:
    """One row per half-hour: the latest forecast published at or before the cutoff on D-1."""
    h, m = parse_cutoff(cutoff)
    actuals, fc = load_store()
    cut = (fc["delivery_midnight"] - pd.Timedelta(days=1) + pd.Timedelta(hours=h, minutes=m)).dt.tz_convert("UTC")
    eligible = fc[fc["publish_time"] <= cut]
    latest = eligible.sort_values("publish_time").drop_duplicates("start_time", keep="last")
    out = latest.merge(actuals, on="start_time", how="left")
    out["error"] = out["forecast"] - out["actual"]
    local = out["start_time"].dt.tz_convert(LONDON)
    out["date"], out["time"], out["hour"] = local.dt.date, local.dt.strftime("%H:%M"), local.dt.hour
    return out.sort_values("start_time").reset_index(drop=True)


def compute_metrics(err: pd.Series) -> dict:
    """Calculate MAE, RMSE, Bias, Median absolute error, and P95 buffer."""
    err = err.dropna()
    if err.empty:
        return {k: None for k in ("mae", "rmse", "bias", "median_abs", "p95")}
    a = err.abs()
    return {
        "mae": round(a.mean(), 1),
        "rmse": round(float(np.sqrt((err ** 2).mean())), 1),
        "bias": round(err.mean(), 1),
        "median_abs": round(a.median(), 1),
        "p95": round(a.quantile(0.95), 1),
    }


def clean_val(v):
    """Normalize NaN and NumPy scalar values for JSON serialization."""
    if v is None:
        return None
    if isinstance(v, (float, np.floating)) and np.isnan(v):
        return None
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v)
    return v


@lru_cache(maxsize=1)
def by_horizon() -> list[dict]:
    """Error vs forecast horizon, using every forecast ever published (independent of cutoff)."""
    actuals, fc = load_store()
    d = fc.merge(actuals, on="start_time", how="inner")
    d["horizon_h"] = ((d["start_time"] - d["publish_time"]).dt.total_seconds() // 3600).astype(int)
    d["abs_err"] = (d["forecast"] - d["actual"]).abs()
    g = d[d["horizon_h"].between(0, 48)].groupby("horizon_h")["abs_err"].mean().round(1)
    return [{"horizon_h": int(h), "mae": float(v)} for h, v in g.items()]

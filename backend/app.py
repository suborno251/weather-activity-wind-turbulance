"""Wind Forecast Monitor: FastAPI backend.

Serves GB national wind forecast vs actual analysis for January 2026 day-ahead decisions.

Run:      uvicorn app:app --reload --port 8000
Refresh:  python app.py refresh      (downloads Elexon data into ./data as CSV)

Key idea: for each half-hour a buyer would have used the LATEST forecast published
before the day-ahead cutoff (HH:MM on the day before delivery, GB local time).
error = forecast - actual, so positive bias means the forecast ran high.
"""
from __future__ import annotations

import os
import sys
from datetime import date as Date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import encoders_by_class_tuples
from fastapi.middleware.cors import CORSMiddleware

# Ensure NumPy scalar types serialize properly in FastAPI responses
encoders_by_class_tuples[int] = (np.integer,)
encoders_by_class_tuples[float] = (np.floating,)

# ----------------------------------------------------------------------------- config
BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data"))
ACTUALS_CSV = DATA_DIR / "actuals.csv"
FORECASTS_CSV = DATA_DIR / "forecasts.csv"

LONDON = "Europe/London"
SCOPE_START = Date(2026, 1, 1)   # delivery days in scope
SCOPE_END = Date(2026, 1, 31)
# Forecasts for 1 Jan can be published on the 31 Dec, so fetch a little earlier.
FETCH_PUBLISH_FROM = datetime(2025, 12, 28)
FETCH_CHUNK_DAYS = int(os.getenv("FETCH_CHUNK_DAYS", "3"))
COMPARE_CUTOFFS = ["06:00", "09:00", "12:00", "15:00"]
PERIODS = [("Night 00:00–06:00", 0, 6), ("Morning 06:00–12:00", 6, 12),
           ("Afternoon 12:00–18:00", 12, 18), ("Evening 18:00–24:00", 18, 24)]

app = FastAPI(title="Wind Forecast Monitor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------- fetching
def _stream(dataset: str, params: dict) -> list[dict]:
    r = requests.get(f"{BASE_URL}/datasets/{dataset}/stream", params=params, timeout=90,
                     headers={"Accept": "application/json"})
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


# ----------------------------------------------------------------------------- data store
@lru_cache(maxsize=1)
def load_store() -> tuple[pd.DataFrame, pd.DataFrame]:
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


def _parse_cutoff(cutoff: str) -> tuple[int, int]:
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
    h, m = _parse_cutoff(cutoff)
    actuals, fc = load_store()
    cut = (fc["delivery_midnight"] - pd.Timedelta(days=1) + pd.Timedelta(hours=h, minutes=m)).dt.tz_convert("UTC")
    eligible = fc[fc["publish_time"] <= cut]
    latest = eligible.sort_values("publish_time").drop_duplicates("start_time", keep="last")
    out = latest.merge(actuals, on="start_time", how="left")
    out["error"] = out["forecast"] - out["actual"]
    local = out["start_time"].dt.tz_convert(LONDON)
    out["date"], out["time"], out["hour"] = local.dt.date, local.dt.strftime("%H:%M"), local.dt.hour
    return out.sort_values("start_time").reset_index(drop=True)


def _metrics(err: pd.Series) -> dict:
    err = err.dropna()
    if err.empty:
        return {k: None for k in ("mae", "rmse", "bias", "median_abs", "p95")}
    a = err.abs()
    return {"mae": round(a.mean(), 1), "rmse": round(float(np.sqrt((err ** 2).mean())), 1),
            "bias": round(err.mean(), 1), "median_abs": round(a.median(), 1),
            "p95": round(a.quantile(0.95), 1)}


def _clean(v):
    if v is None:
        return None
    if isinstance(v, (float, np.floating)) and np.isnan(v):
        return None
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v)
    return v


# ----------------------------------------------------------------------------- endpoints
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/decision")
def decision(date: Date, cutoff: str = Query("12:00")):
    if not (SCOPE_START <= date <= SCOPE_END):
        raise HTTPException(422, "date must be in January 2026")
    df = latest_before_cutoff(cutoff)
    day = df[df["date"] == date]
    if day.empty:
        raise HTTPException(404, "No forecast available for that day and cutoff")

    err = df["error"].dropna()
    q05, q95 = (err.quantile(0.05), err.quantile(0.95)) if not err.empty else (0.0, 0.0)
    peak = day.loc[day["forecast"].idxmax()]

    series = [{
        "time": r.time,
        "forecast": _clean(r.forecast),
        "actual": _clean(r.actual),
        "lower": round(max(float(r.forecast - q95), 0.0), 1),   # actual = forecast - error
        "upper": round(float(r.forecast - q05), 1),
    } for r in day.itertuples()]

    periods = []
    for label, h0, h1 in PERIODS:
        mask_day = day["hour"].between(h0, h1 - 1)
        p95 = df.loc[df["hour"].between(h0, h1 - 1), "error"].abs().quantile(0.95)
        avg = day.loc[mask_day, "forecast"].mean()
        periods.append({"label": label, "forecast_mw": round(float(avg), 1),
                        "p95_error_mw": round(float(p95), 1), "low_wind_mw": round(max(float(avg - p95), 0.0), 1)})

    return {"kpis": {"peak_mw": round(float(peak["forecast"]), 1), "peak_time": peak["time"],
                     "avg_mw": round(float(day["forecast"].mean()), 1)},
            "series": series, "periods": periods}


@lru_cache(maxsize=1)
def _by_horizon() -> list[dict]:
    """Error vs forecast horizon, using every forecast ever published (independent of cutoff)."""
    actuals, fc = load_store()
    d = fc.merge(actuals, on="start_time", how="inner")
    d["horizon_h"] = ((d["start_time"] - d["publish_time"]).dt.total_seconds() // 3600).astype(int)
    d["abs_err"] = (d["forecast"] - d["actual"]).abs()
    g = d[d["horizon_h"].between(0, 48)].groupby("horizon_h")["abs_err"].mean().round(1)
    return [{"horizon_h": int(h), "mae": float(v)} for h, v in g.items()]


@app.get("/api/accuracy")
def accuracy(cutoff: str = Query("12:00")):
    df = latest_before_cutoff(cutoff)
    err = df["error"].dropna()
    if err.empty:
        raise HTTPException(404, "No overlapping forecast/actual data")

    daily = df.groupby("date")["error"].apply(lambda s: s.abs().mean()).dropna()
    by_slot = df.groupby("time")["error"].apply(lambda s: s.abs().mean()).dropna()

    limit = max(100, int(np.ceil(err.abs().quantile(0.99) / 100) * 100))
    edges = np.linspace(-limit, limit, 21)
    counts, _ = np.histogram(err.clip(-limit, limit), bins=edges)

    cutoffs = sorted(set(COMPARE_CUTOFFS) | {cutoff})
    comparison = [{"cutoff": c, **{k: v for k, v in _metrics(latest_before_cutoff(c)["error"]).items()
                                   if k in ("mae", "rmse", "bias", "p95")}} for c in cutoffs]

    return {
        "metrics": _metrics(err),
        "daily": [{"date": d.strftime("%d %b"), "mae": round(v, 1)} for d, v in daily.items()],
        "histogram": [{"bin": str(int(e)), "count": int(c)} for e, c in zip(edges[:-1], counts)],
        "by_slot": [{"slot": t, "mae": round(v, 1)} for t, v in by_slot.items()],
        "by_horizon": _by_horizon(),
        "cutoff_comparison": comparison,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        refresh_data()
        print(f"Saved {ACTUALS_CSV} and {FORECASTS_CSV}")
    else:
        print("Usage: python app.py refresh   |   uvicorn app:app --port 8000")

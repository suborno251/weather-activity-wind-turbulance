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
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

# Ensure NumPy scalar types serialize properly in FastAPI responses
encoders_by_class_tuples[int] = (np.integer,)
encoders_by_class_tuples[float] = (np.floating,)

# ----------------------------------------------------------------------------- schemas
class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Service health status", json_schema_extra={"example": "ok"})


class SeriesPoint(BaseModel):
    time: str = Field(description="Half-hour slot time (HH:MM) in GB local time", json_schema_extra={"example": "12:00"})
    forecast: float | None = Field(description="Wind generation forecast in MW", json_schema_extra={"example": 8500.5})
    actual: float | None = Field(description="Actual wind generation delivered in MW", json_schema_extra={"example": 8210.0})
    lower: float = Field(description="P5 conservative lower bound (forecast - Q95 error)", json_schema_extra={"example": 6800.0})
    upper: float = Field(description="P95 upper bound (forecast - Q05 error)", json_schema_extra={"example": 9600.0})


class ProcurementPeriod(BaseModel):
    label: str = Field(description="Delivery block label", json_schema_extra={"example": "Morning 06:00–12:00"})
    forecast_mw: float = Field(description="Mean expected wind generation in MW", json_schema_extra={"example": 7400.2})
    p95_error_mw: float = Field(description="Historical P95 error buffer in MW", json_schema_extra={"example": 1850.0})
    low_wind_mw: float = Field(description="Conservative baseline generation (Forecast - P95 buffer)", json_schema_extra={"example": 5550.2})


class DecisionKpis(BaseModel):
    peak_mw: float = Field(description="Peak expected wind generation across delivery day in MW", json_schema_extra={"example": 11200.0})
    peak_time: str = Field(description="Time of peak wind generation", json_schema_extra={"example": "14:30"})
    avg_mw: float = Field(description="Daily average expected wind generation in MW", json_schema_extra={"example": 8100.5})


class DecisionResponse(BaseModel):
    kpis: DecisionKpis = Field(description="High-level day summary KPIs")
    series: list[SeriesPoint] = Field(description="48 half-hour settlement slot forecast vs actual series with uncertainty bands")
    periods: list[ProcurementPeriod] = Field(description="4-block operational procurement planning breakdown")


class Metrics(BaseModel):
    mae: float | None = Field(description="Mean Absolute Error in MW", json_schema_extra={"example": 1450.5})
    rmse: float | None = Field(description="Root Mean Square Error in MW", json_schema_extra={"example": 1890.2})
    bias: float | None = Field(description="Mean error in MW (forecast - actual, positive = over-forecast)", json_schema_extra={"example": 120.3})
    median_abs: float | None = Field(description="Median absolute error in MW", json_schema_extra={"example": 1150.0})
    p95: float | None = Field(description="95th percentile absolute error buffer in MW", json_schema_extra={"example": 3200.0})


class DailyAccuracy(BaseModel):
    date: str = Field(description="Delivery date (DD Mon)", json_schema_extra={"example": "15 Jan"})
    mae: float = Field(description="Mean Absolute Error for this day in MW", json_schema_extra={"example": 1620.4})


class HistogramBin(BaseModel):
    bin: str = Field(description="Error bin start in MW", json_schema_extra={"example": "-1000"})
    count: int = Field(description="Frequency count of half-hour slots in this bin", json_schema_extra={"example": 42})


class SlotAccuracy(BaseModel):
    slot: str = Field(description="Half-hour slot time (HH:MM)", json_schema_extra={"example": "17:30"})
    mae: float = Field(description="Mean Absolute Error across month for this slot in MW", json_schema_extra={"example": 1820.0})


class HorizonDecay(BaseModel):
    horizon_h: int = Field(description="Forecast horizon hours ahead of delivery", json_schema_extra={"example": 24})
    mae: float = Field(description="Mean Absolute Error in MW", json_schema_extra={"example": 1950.0})


class CutoffComparisonItem(BaseModel):
    cutoff: str = Field(description="Gate closure cutoff time", json_schema_extra={"example": "12:00"})
    mae: float | None = Field(description="Mean Absolute Error in MW", json_schema_extra={"example": 1450.5})
    rmse: float | None = Field(description="Root Mean Square Error in MW", json_schema_extra={"example": 1890.2})
    bias: float | None = Field(description="Signed bias in MW", json_schema_extra={"example": 120.3})
    p95: float | None = Field(description="P95 error buffer in MW", json_schema_extra={"example": 3200.0})


class AccuracyResponse(BaseModel):
    metrics: Metrics = Field(description="Overall aggregate error KPIs for selected cutoff")
    daily: list[DailyAccuracy] = Field(description="Daily MAE timeline across January 2026")
    histogram: list[HistogramBin] = Field(description="Error distribution histogram bins")
    by_slot: list[SlotAccuracy] = Field(description="Diurnal error profile by settlement half-hour")
    by_horizon: list[HorizonDecay] = Field(description="Error decay by forecast publication horizon (0–48h)")
    cutoff_comparison: list[CutoffComparisonItem] = Field(description="Accuracy comparison across standard industry cutoffs")


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

tags_metadata = [
    {
        "name": "Decision Support",
        "description": "Day-ahead forecast evaluation with gate-closure cutoff filtering and procurement risk buffers.",
    },
    {
        "name": "Forecast Accuracy",
        "description": "Historical error analysis including MAE, RMSE, diurnal bias, horizon decay, and cutoff benchmarking.",
    },
    {
        "name": "System",
        "description": "Operational health check and diagnostics.",
    },
]

app = FastAPI(
    title="Wind Forecast Monitor API",
    description="""
## Day-Ahead Wind Forecast & Procurement Portal API

Interactive Swagger API for GB national renewable wind generation analysis based on Elexon BMRS data (**January 2026**).

### Features:
- **Decision View**: Reproduces exact forecasts known prior to cutoff on $D-1$ and calculates procurement buffers.
- **Accuracy View**: Measures historical forecast accuracy (MAE, RMSE, Bias, P95) and cutoff comparisons.
- **Interactive Documentation**: Test endpoints live with Swagger UI below or via `/docs` and `/redoc`.
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------- Swagger/Docs aliases
@app.get("/swagger", include_in_schema=False)
def swagger_ui_redirect():
    """Redirect /swagger to /docs."""
    return RedirectResponse(url="/docs")


@app.get("/api/docs", include_in_schema=False)
def api_docs_ui():
    """Serve Swagger UI directly under /api/docs for reverse proxies that only expose /api."""
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="Wind Forecast Monitor API - Swagger UI")


@app.get("/api/openapi.json", include_in_schema=False)
def api_openapi_schema():
    """Serve OpenAPI JSON schema under /api for reverse proxies."""
    return app.openapi()


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
@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service Health Check",
)
def health():
    """Verify backend API health status."""
    return {"status": "ok"}


@app.get(
    "/api/decision",
    response_model=DecisionResponse,
    tags=["Decision Support"],
    summary="Day-Ahead Forecast & Procurement Decision Snapshot",
)
def decision(
    date: Date = Query(..., description="Delivery date in January 2026 (YYYY-MM-DD)", examples=["2026-01-15"]),
    cutoff: str = Query("12:00", description="Gate closure decision cutoff time on D-1 (HH:MM in 24h format)", examples=["12:00"]),
):
    """Retrieve the wind forecast known prior to gate closure on D-1 for the delivery day.

    Calculates:
    - 48 half-hour settlement slots with forecast, actual generation, and uncertainty bounds.
    - 4 operational delivery periods with conservative low-wind procurement baselines.
    - Day-level peak and average expected generation KPIs.
    """
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


@app.get(
    "/api/accuracy",
    response_model=AccuracyResponse,
    tags=["Forecast Accuracy"],
    summary="Aggregate Accuracy Metrics & Cutoff Benchmarks",
)
def accuracy(
    cutoff: str = Query("12:00", description="Gate closure cutoff time on D-1 (HH:MM in 24h format)", examples=["12:00"]),
):
    """Compute aggregate accuracy metrics across January 2026 for the given decision cutoff.

    Includes:
    - Key metrics (MAE, RMSE, Bias, Median Absolute Error, P95 risk buffer).
    - Daily MAE breakdown across the entire delivery month.
    - Error distribution histogram.
    - Diurnal accuracy patterns by 30-minute settlement slot.
    - Forecast accuracy decay by publish horizon (0 to 48 hours).
    - Multi-cutoff benchmark comparison table.
    """
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

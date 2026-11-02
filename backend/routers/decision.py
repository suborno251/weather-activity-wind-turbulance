"""Decision support router for day-ahead power purchasing."""
from __future__ import annotations

from datetime import date as Date

from fastapi import APIRouter, HTTPException, Query

from config import PERIODS, SCOPE_END, SCOPE_START
from schemas import DecisionResponse
from services.analysis import clean_val, latest_before_cutoff

router = APIRouter(tags=["Decision Support"])


@router.get(
    "/api/decision",
    response_model=DecisionResponse,
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
        "forecast": clean_val(r.forecast),
        "actual": clean_val(r.actual),
        "lower": round(max(float(r.forecast - q95), 0.0), 1),   # actual = forecast - error
        "upper": round(float(r.forecast - q05), 1),
    } for r in day.itertuples()]

    periods = []
    for label, h0, h1 in PERIODS:
        mask_day = day["hour"].between(h0, h1 - 1)
        p95 = df.loc[df["hour"].between(h0, h1 - 1), "error"].abs().quantile(0.95)
        avg = day.loc[mask_day, "forecast"].mean()
        periods.append({
            "label": label,
            "forecast_mw": round(float(avg), 1),
            "p95_error_mw": round(float(p95), 1),
            "low_wind_mw": round(max(float(avg - p95), 0.0), 1),
        })

    return {
        "kpis": {
            "peak_mw": round(float(peak["forecast"]), 1),
            "peak_time": peak["time"],
            "avg_mw": round(float(day["forecast"].mean()), 1),
        },
        "series": series,
        "periods": periods,
    }

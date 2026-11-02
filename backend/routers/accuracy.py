"""Accuracy metrics and cutoff benchmarking router."""
from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from config import COMPARE_CUTOFFS
from schemas import AccuracyResponse
from services.analysis import by_horizon, compute_metrics, latest_before_cutoff

router = APIRouter(tags=["Forecast Accuracy"])


@router.get(
    "/api/accuracy",
    response_model=AccuracyResponse,
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
    comparison = [
        {
            "cutoff": c,
            **{
                k: v
                for k, v in compute_metrics(latest_before_cutoff(c)["error"]).items()
                if k in ("mae", "rmse", "bias", "p95")
            },
        }
        for c in cutoffs
    ]

    return {
        "metrics": compute_metrics(err),
        "daily": [{"date": d.strftime("%d %b"), "mae": round(v, 1)} for d, v in daily.items()],
        "histogram": [{"bin": str(int(e)), "count": int(c)} for e, c in zip(edges[:-1], counts)],
        "by_slot": [{"slot": t, "mae": round(v, 1)} for t, v in by_slot.items()],
        "by_horizon": by_horizon(),
        "cutoff_comparison": comparison,
    }
